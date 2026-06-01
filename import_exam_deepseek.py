"""
import_exam_deepseek.py — Pipeline import đề thi từ MinerU output.

Pipeline:
  Bước 1: smart_parser phân tích markdown → danh sách câu hỏi (thuần regex, không LLM)
  Bước 2: Upload ảnh lên Supabase Storage (fallback về web/public/exam-images)
  Bước 3: Insert vào Supabase qua psycopg2

Usage:
  python import_exam_deepseek.py                    # liệt kê đề có sẵn
  python import_exam_deepseek.py <số thứ tự>        # import theo số
  python import_exam_deepseek.py <keyword>           # import theo tên (vd: "Cau Giay")
  python import_exam_deepseek.py <số> "Tên đẹp" 2026
"""
import asyncio
import logging
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

load_dotenv()

# Fix Windows terminal UTF-8 (cần cho ký tự tiếng Việt trong Rich)
if sys.platform == "win32" and hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8" and not getattr(sys.stdout, "_custom_utf8", False):
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._custom_utf8 = True
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from database import db

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_path=False)],
)
logger = logging.getLogger(__name__)
console = Console()

# ─── Cấu hình ────────────────────────────────────────────────────────────────

MINERU_DIR = Path("C:/Users/HP/MinerU")
IMAGE_PUBLIC_DIR = Path(__file__).parent / "web" / "public" / "exam-images"
SUPABASE_PROJECT_ID = "zabvdgnucfanvbjjgnic"
SUPABASE_URL = f"https://{SUPABASE_PROJECT_ID}.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

async def _upload_image(
    abs_path: Path,
    exam_folder_name: str,
    session: aiohttp.ClientSession,
) -> str:
    """Upload 1 ảnh lên Supabase Storage, fallback về local static nếu lỗi."""
    bucket = "exam-images"
    storage_path = f"{exam_folder_name}/{abs_path.name}"

    if SUPABASE_SERVICE_KEY:
        upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"
        try:
            with open(abs_path, "rb") as f:
                data = f.read()
            headers = {
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "image/jpeg",
            }
            async with session.post(upload_url, data=data, headers=headers) as resp:
                if resp.status in (200, 201):
                    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"
                logger.warning(f"  Storage {resp.status}: {abs_path.name}")
        except Exception as e:
            logger.warning(f"  Storage upload lỗi: {e}")

    # Fallback: copy vào web/public/exam-images/
    IMAGE_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGE_PUBLIC_DIR / abs_path.name
    if not dest.exists():
        shutil.copy2(abs_path, dest)
    return f"/exam-images/{abs_path.name}"


# ═══════════════════════════════════════════════════════════════════════════════
# DB INSERT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

_LEVEL_MAP = {
    "nhận biết": "Nhận biết",
    "thong hieu": "Thông hiểu",
    "thông hiểu": "Thông hiểu",
    "vận dụng cao": "Vận dụng cao",
    "van dung cao": "Vận dụng cao",
    "vận dụng": "Vận dụng",
    "van dung": "Vận dụng",
}

_SECTION_QTYPE = {1: "trac_nghiem", 2: "dung_sai", 3: "tu_luan"}


def _part_section(part: str) -> int:
    m = re.search(r'(\d+)', part)
    return int(m.group(1)) if m else 1


def _options_to_dict(options: list) -> Optional[dict]:
    """["A. nội dung", "B. nội dung"] → {"A": "nội dung", "B": "nội dung"}"""
    if not options:
        return None
    result = {}
    for opt in options:
        m = re.match(r'^([A-Da-d])[.):\s]+(.+)', str(opt).strip(), re.DOTALL)
        if m:
            result[m.group(1).upper()] = m.group(2).strip()
    return result or None


def insert_to_supabase(final_json_data: dict, exam_id: int, subject_id: int) -> bool:
    """Insert 1 câu đã xử lý vào bảng questions."""
    part = final_json_data.get("part", "part_1")
    q_num = final_json_data.get("question_index", 0)
    section = _part_section(part)
    q_type = _SECTION_QTYPE.get(section, "trac_nghiem")

    question_text = final_json_data.get("question_text", "")
    options_list = final_json_data.get("options") or []
    correct_answer = final_json_data.get("correct_answer")
    explanation_val = final_json_data.get("explanation") or None
    raw_content = final_json_data.get("raw_content", "")
    topic_name = str(final_json_data.get("topic") or "").strip()
    level_raw = str(final_json_data.get("level") or "").strip()
    level_clean = _LEVEL_MAP.get(level_raw.lower(), level_raw)

    topic_id: Optional[int] = None
    if topic_name and subject_id:
        try:
            topic_id = db.get_or_create_topic(subject_id, topic_name)
        except Exception:
            pass

    options_dict = _options_to_dict(options_list)

    full_text = question_text + " ".join(options_list)
    has_formula = bool(re.search(r'\$[^$]+\$|\$\$[\s\S]+?\$\$', full_text))
    has_image = bool(re.search(r'!\[.*?\]\(.*?\)', full_text))
    has_table = bool(re.search(r'<table|\|.+\|', full_text))

    # question_number: P1 → 1-12, P2 → 101-104, P3 → 201-206
    question_number = q_num + (section - 1) * 100

    # classification_meta: thêm cờ review nếu entry point gắn (pipeline Azota)
    meta = {"section": section, "topic": topic_name}
    if final_json_data.get("needs_review"):
        meta["needs_review"] = True
        meta["review_reason"] = final_json_data.get("review_reason", "")

    try:
        db.insert_question(
            exam_id=exam_id,
            subject_id=subject_id,
            topic_id=topic_id,
            question_number=question_number,
            content=question_text,
            content_raw=raw_content,
            question_type=q_type,
            level=level_clean,
            level_confidence=0.9,
            options=options_dict,
            correct_answer=str(correct_answer) if correct_answer is not None else None,
            explanation=str(explanation_val) if explanation_val else None,
            has_formula=has_formula,
            has_image=has_image,
            has_table=has_table,
            classification_meta=meta,
        )
        return True
    except Exception as e:
        logger.error(f"  DB insert lỗi [{part}] câu {q_num}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# METADATA & TOPIC DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Keywords để classify topic từ nội dung câu hỏi (subject_id → [(topic_name, [keywords])])
_TOPIC_KEYWORDS: dict[int, list[tuple[str, list[str]]]] = {
    1: [  # Toán
        ("Giải tích - Hàm số",                  ["hàm số", "đơn điệu", "đồng biến", "nghịch biến", "cực trị", "cực đại", "cực tiểu", "tiệm cận"]),
        ("Giải tích - Đạo hàm",                 ["đạo hàm", "vi phân", "tiếp tuyến"]),
        ("Giải tích - Tích phân",               ["tích phân", "nguyên hàm", "diện tích hình phẳng"]),
        ("Giải tích - Lũy thừa & Logarit",      ["logarit", "lũy thừa", r"\bln\b", r"\blog\b", "mũ", "phương trình mũ", "phương trình logarit"]),
        ("Hình học - Hình học không gian",       ["khối hộp", "hình chóp", "hình cầu", "hình trụ", "hình nón", "thể tích", "diện tích toàn phần", "đường thẳng song song"]),
        ("Hình học - Tọa độ không gian Oxyz",   ["oxyz", "mặt phẳng", "véc tơ pháp", "phương trình mặt phẳng", "đường thẳng trong không gian"]),
        ("Hình học - Tọa độ phẳng Oxy",         ["đường thẳng", "parabol", "elip", "hyperbol", "tọa độ"]),
        ("Hình học - Hình học phẳng",            ["tam giác", "tứ giác", "đường tròn", "nội tiếp", "ngoại tiếp"]),
        ("Đại số - Tổ hợp & Xác suất",          ["tổ hợp", "chỉnh hợp", "xác suất", "hoán vị", "biến cố", "quy tắc cộng", "quy tắc nhân"]),
        ("Đại số - Số phức",                     ["số phức", "phần thực", "phần ảo", "modun", "argument"]),
        ("Đại số - Dãy số & Cấp số",            ["cấp số cộng", "cấp số nhân", "dãy số", "công sai", "công bội", "tổng n số hạng"]),
        ("Đại số - Phương trình & Bất phương trình", ["phương trình", "bất phương trình", "hệ phương trình"]),
    ],
    2: [  # Vật Lý
        ("Vật lý hạt nhân",          ["hạt nhân", "phóng xạ", "urani", "bohr", r"\balpha\b", r"\bbeta\b", "nơtron", "proton", "chu kỳ bán rã"]),
        ("Cơ học - Dao động cơ",     ["dao động", "chu kỳ", "tần số", "con lắc", "biên độ", "pha ban đầu"]),
        ("Nhiệt học",                ["nội năng", "đông đặc", "nóng chảy", "bay hơi", "kelvin", "celsius", "nhiệt lượng", "nhiệt dung"]),
        ("Điện xoay chiều",          ["điện xoay chiều", "suất điện động", "cuộn dây", "tụ điện", "công suất điện", "trở kháng", "hệ số công suất"]),
        ("Sóng cơ",                  ["sóng cơ", "giao thoa sóng", "siêu âm", "tốc độ sóng", "bước sóng", "sóng dừng"]),
        ("Quang học - Sóng ánh sáng", ["tia sáng", "lăng kính", "thấu kính", "gương", "phản xạ toàn phần", "khúc xạ", "giao thoa ánh sáng"]),
        ("Điện từ - Dao động & Sóng điện từ", ["từ trường", "cảm ứng điện từ", "sóng điện từ", "dao động điện từ"]),
        ("Quang học - Lượng tử ánh sáng", ["quang điện", "photon", "einstein", "công thoát", "bước sóng giới hạn"]),
    ],
    3: [  # Hóa Học
        ("Hóa hữu cơ - Polymer",                ["polime", "polymer", "cao su", "tơ", "nhựa", "chất dẻo", "teflon", "nylon"]),
        ("Hóa hữu cơ - Amine & Amino acid & Protein", ["amin", "amino axit", "protein", "peptit", "liên kết peptit"]),
        ("Hóa hữu cơ - Carbohydrate",           ["glucozơ", "saccarozơ", "tinh bột", "xenlulozơ", "fructozơ", "mantozơ"]),
        ("Hóa hữu cơ - Ancol & Phenol",         ["ancol", "phenol", "etanol", "methanol", "glixerol"]),
        ("Hóa hữu cơ - Aldehyde & Ketone & Acid Carboxylic", ["anđehit", "xeton", "axit cacboxylic", "fomandehit", "axetanđehit"]),
        ("Hóa hữu cơ - Hydrocarbon",            ["ankan", "anken", "ankyn", "benzen", "hiđrocacbon", "phản ứng cộng", "phản ứng thế"]),
        ("Hóa vô cơ - Kim loại",                ["kim loại", "sắt", "đồng", "nhôm", "kẽm", "điện phân", "ăn mòn", "dãy điện hóa"]),
        ("Hóa vô cơ - Điện phân & Ăn mòn",     ["điện phân", "ăn mòn điện hóa", "ăn mòn hóa học", "bảo vệ kim loại"]),
        ("Hóa vô cơ - Phi kim",                  ["oxi", "lưu huỳnh", "nitơ", "photpho", "clo", "halogen", "axit sunfuric"]),
        ("Hóa đại cương - Phản ứng hóa học",    ["tốc độ phản ứng", "cân bằng hóa học", "nhiệt phản ứng", "nguyên lí le chatelier"]),
    ],
    6: [  # Lịch Sử
        ("Cách mạng Việt Nam",            ["cách mạng tháng 8", "1945", "bác hồ", "hồ chí minh", "mặt trận việt minh", "tổng khởi nghĩa"]),
        ("Lịch sử Việt Nam hiện đại",    ["kháng chiến chống pháp", "kháng chiến chống mỹ", "giải phóng miền nam", "thống nhất đất nước"]),
        ("Lịch sử thế giới hiện đại",    ["liên xô", "chiến tranh lạnh", "trật tự thế giới", "liên hợp quốc", "mỹ", "châu âu"]),
        ("Chiến tranh thế giới",          ["thế chiến", "chiến tranh thế giới thứ", "phát xít", "đồng minh", "hitle", "nhật bản"]),
    ],
    9: [  # Tiếng Anh
        ("Đọc hiểu",                    ["read the following", "passage", "according to", "the text says", "best answer"]),
        ("Điền từ vào đoạn văn",        ["blank", "fill in", "choose the word", "passage below"]),
        ("Ngữ pháp - Câu điều kiện",   ["conditional", "if clause", "if i were", "provided that"]),
        ("Ngữ pháp - Câu bị động",     ["passive voice", "be + v3", "was built", "is known"]),
        ("Ngữ pháp - Mệnh đề quan hệ", ["relative clause", "who", "which", "that refers"]),
        ("Từ vựng & Collocation",       ["synonym", "antonym", "closest in meaning", "most nearly means"]),
    ],
}


def _detect_topic(subject_id: int, question_text: str) -> str:
    """Classify topic từ nội dung câu hỏi dựa trên keyword matching."""
    keywords_list = _TOPIC_KEYWORDS.get(subject_id, [])
    text_lower = question_text.lower()
    for topic_name, keywords in keywords_list:
        for kw in keywords:
            if re.search(kw, text_lower):
                return topic_name
    return "Chủ đề chung"


def _detect_exam_type(title: str) -> str:
    t = unicodedata.normalize("NFC", title).lower()
    on_kws = (unicodedata.normalize("NFC", "ôn tập"), unicodedata.normalize("NFC", "ôn thi"), "on tap", "on thi")
    ks_kws = (unicodedata.normalize("NFC", "khảo sát"), "khao sat")
    if any(k in t for k in on_kws):
        return "on_thi"
    if any(k in t for k in ks_kws):
        return "KS"
    return "thi_thu"


def _create_exam_record(title: str, year: int, subject_id: int) -> int:
    exam_type = _detect_exam_type(title)
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO exams (title, year, exam_type, subject_id, ocr_status)
                   VALUES (%s, %s, %s, %s, 'done') RETURNING id""",
                (title, year, exam_type, subject_id),
            )
            exam_id = cur.fetchone()[0]
        conn.commit()
    return exam_id


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

async def run_pipeline(
    exam_folder: Path,
    exam_title: str,
    exam_year: int,
    subject_id: int,
) -> None:
    console.print(Panel(
        f"[bold]{exam_title}[/] ({exam_year})\n"
        f"[dim]{exam_folder.name[:80]}[/]",
        style="cyan",
    ))

    md_path = exam_folder / "full.md"
    if not md_path.exists():
        console.print(f"[red]  Không tìm thấy {md_path}[/]")
        return
    raw_md = md_path.read_text(encoding="utf-8")
    console.print(f"  Markdown: {len(raw_md):,} chars")

    # Bước 1: smart_parser (thuần regex, không LLM)
    console.print("  [yellow]Bước 1: smart_parser...[/]")
    from processor.smart_parser import parse_exam_file
    parsed_exams = parse_exam_file(raw_md)
    if not parsed_exams:
        console.print("[red]  smart_parser không tìm thấy đề thi nào.[/]")
        return

    exam = parsed_exams[0]
    console.print(
        f"  [green]smart_parser OK[/] → môn: {exam.subject}, "
        f"mã đề: {exam.ma_de}, tổng: {len(exam.questions)} câu"
    )

    # Bước 2: Tạo exam record trong DB
    exam_id = _create_exam_record(exam_title, exam_year, subject_id)

    # Bước 3: Upload ảnh + Insert DB
    console.print("  [yellow]Bước 2-3: Upload ảnh và Insert DB...[/]")
    async with aiohttp.ClientSession() as http_session:
        ok = err = 0
        for q in exam.questions:
            question_text = q.question_text
            raw_content = q.raw_text

            # Upload ảnh, thay local path → public URL
            for local_path in q.image_paths:
                abs_path = exam_folder / local_path
                if abs_path.exists():
                    try:
                        public_url = await _upload_image(abs_path, exam_folder.name, http_session)
                        question_text = question_text.replace(f"({local_path})", f"({public_url})")
                        raw_content = raw_content.replace(f"({local_path})", f"({public_url})")
                    except Exception as e:
                        logger.warning(f"  Câu {q.index} ảnh lỗi: {e}")

            options_list = []
            if q.options:
                for k, v in sorted(q.options.items()):
                    options_list.append(f"{k}. {v}")

            final_data = {
                "part": f"part_{q.section}",
                "question_index": q.index,
                "question_text": question_text,
                "options": options_list,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "topic": _detect_topic(subject_id, question_text),
                "level": "Thông hiểu",
                "raw_content": raw_content,
            }

            if insert_to_supabase(final_data, exam_id, subject_id):
                ok += 1
            else:
                err += 1

    console.print(
        f"  [green]Hoàn tất[/] | exam_id={exam_id} | "
        f"[green]{ok} câu thành công[/]"
        + (f"  [red]{err} lỗi[/]" if err else "")
    )
    console.print(f"  → http://localhost:3000/exams\n")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def _list_exams() -> list[Path]:
    if not MINERU_DIR.exists():
        return []
    return sorted([
        f for f in MINERU_DIR.iterdir()
        if f.is_dir() and (f / "full.md").exists()
    ])


def _find_exam(keyword: str) -> Optional[Path]:
    def strip_accent(s: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", s)
            if unicodedata.category(c) != "Mn"
        ).lower()
    kw = strip_accent(keyword)
    for folder in _list_exams():
        if kw in strip_accent(folder.name):
            return folder
    return None


def main() -> None:
    db.init_pool()
    subject_id = db.get_subject_id("TOAN")
    exams = _list_exams()

    if len(sys.argv) == 1:
        if not exams:
            console.print(f"[red]Không tìm thấy đề trong {MINERU_DIR}[/]")
            return
        t = Table(show_header=True, header_style="bold cyan")
        t.add_column("#", justify="right", width=3)
        t.add_column("Tên thư mục đề thi", max_width=75)
        for i, f in enumerate(exams, 1):
            name = f.name.rsplit("-", 5)[0].replace(".pdf", "")
            t.add_row(str(i), name)
        console.print(t)
        console.print(
            "\n[dim]Dùng: python import_exam_deepseek.py <số>\n"
            "Hoặc: python import_exam_deepseek.py <số> \"Tên đẹp\" 2026[/]"
        )
        return

    selector = sys.argv[1]
    exam_title: Optional[str] = sys.argv[2] if len(sys.argv) > 2 else None
    exam_year = int(sys.argv[3]) if len(sys.argv) > 3 else 2026

    if selector.isdigit():
        idx = int(selector) - 1
        if idx < 0 or idx >= len(exams):
            console.print(f"[red]Số thứ tự {selector} không hợp lệ (1–{len(exams)})[/]")
            return
        exam_folder = exams[idx]
    else:
        exam_folder = _find_exam(selector)
        if not exam_folder:
            console.print(f"[red]Không tìm thấy đề khớp '{selector}'[/]")
            return

    if not exam_title:
        exam_title = (
            exam_folder.name.rsplit("-", 5)[0]
            .replace(".pdf", "")
            .replace("2026_", "")
            .strip()
        )

    asyncio.run(run_pipeline(exam_folder, exam_title, exam_year, subject_id))


if __name__ == "__main__":
    main()
