"""
import_exam_deepseek.py — Pipeline 4 bước dùng DeepSeek-V3 (tối ưu chi phí).

Pipeline:
  Bước 1: DeepSeek chuẩn hóa markdown thô → chuẩn EXAM-TAG-12
  Bước 2: Python regex cắt thành danh sách câu hỏi
  Bước 3: DeepSeek trích xuất JSON từng câu (async + semaphore + JSON repair)
  Bước 4: Insert vào Supabase qua psycopg2

Usage:
  python import_exam_deepseek.py                    # liệt kê đề có sẵn
  python import_exam_deepseek.py <số thứ tự>        # import theo số
  python import_exam_deepseek.py <keyword>           # import theo tên (vd: "Cau Giay")
  python import_exam_deepseek.py <số> "Tên đẹp" 2026
"""
import asyncio
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from openai import AsyncOpenAI
from rich.console import Console
from rich.logging import RichHandler
from processor.parser_v2 import parse_exam as _parser_v2_parse
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
import config
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
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # để trống → dùng local static

CHUNK_SIZE = 12_000   # ký tự tối đa mỗi chunk gửi lên DeepSeek
CONCURRENCY = 5       # số câu xử lý song song ở Bước 3

deepseek = AsyncOpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)


# ═══════════════════════════════════════════════════════════════════════════════
# BƯỚC 1 — Chuẩn hóa Markdown dùng DeepSeek
# ═══════════════════════════════════════════════════════════════════════════════

_NORMALIZE_SYSTEM = """\
Bạn là chuyên gia xử lý đề thi THPT Việt Nam (Toán, Vật Lý, Hóa Học, Lịch Sử, Tiếng Anh).
Nhiệm vụ: nhận đoạn Markdown thô từ MinerU OCR và chuẩn hóa theo bộ quy tắc EXAM-TAG-12.

QUY TẮC EXAM-TAG-12 (TUYỆT ĐỐI tuân thủ):
1. Tiêu đề 3 phần: ==PHAN 1==  ==PHAN 2==  ==PHAN 3== — mỗi cái trên dòng riêng. Nếu đề thi không chia phần (ví dụ như đề Tiếng Anh chỉ có trắc nghiệm), không cần thêm các thẻ phần này.
2. Đầu mỗi câu hỏi: [CAU 1]  [CAU 2]  ...  [CAU N] — bắt buộc ở đầu dòng mới.
3. Đáp án trắc nghiệm (Phần I hoặc trắc nghiệm thường): Bắt buộc chuyển các lựa chọn trắc nghiệm thành định dạng:
   [A]. <nội dung lựa chọn A>
   [B]. <nội dung lựa chọn B>
   [C]. <nội dung lựa chọn C>
   [D]. <nội dung lựa chọn D>
   Mỗi lựa chọn nằm trên một dòng riêng biệt. BẮT BUỘC phải giữ nguyên toàn bộ nội dung chữ (text) của các phương án trắc nghiệm, tuyệt đối không được bỏ trống hoặc xóa mất nội dung của phương án.
4. Ý đúng/sai (Phần II): Bắt buộc chuyển thành định dạng:
   [a]. <nội dung ý phụ a>
   [b]. <nội dung ý phụ b>
   [c]. <nội dung ý phụ c>
   [d]. <nội dung ý phụ d>
   Mỗi ý nằm trên dòng riêng biệt và bắt buộc giữ nguyên toàn bộ nội dung chữ của từng ý phụ.
5. Nếu tìm thấy bảng đáp án cuối đề: khớp đáp án vào cuối mỗi câu dưới dạng [DAPAN: X]
   (X ví dụ: A, B, DSDD, 1.5). Đặt ngay sau nội dung câu, trước [CAU N+1].
6. GIỮ NGUYÊN 100% công thức LaTeX ($...$, $$...$$) và thẻ ảnh ![](images/...).
7. Sửa lỗi OCR (chữ dính, ký tự vỡ, thiếu dấu tiếng Việt) nhưng KHÔNG thêm/bỏ câu.
8. KHÔNG giải thích, KHÔNG thêm tiêu đề markdown khác, KHÔNG bình luận.
9. LỜI GIẢI — QUAN TRỌNG: Nếu sau nội dung câu (đặc biệt Phần III) xuất hiện phần
   "Lời giải", "Hướng dẫn giải", "Giải:", "Đáp án - Lời giải", "Hướng dẫn" hoặc tương tự:
   - KHÔNG tạo thêm [CAU N+1] mới cho phần đó.
   - Thay vào đó, đặt toàn bộ lời giải VÀO CUỐI câu hiện tại với tag:
     [LOIGIAI: <nội dung lời giải đầy đủ, giữ nguyên LaTeX và ảnh>]
   - Tag [LOIGIAI:...] phải nằm SAU [DAPAN:...] (nếu có) và TRƯỚC [CAU N+1] tiếp theo.
   - Ví dụ đúng:
     [CAU 1] Tính tích phân $\\int_0^1 x^2 dx$.
     [DAPAN: 1/3]
     [LOIGIAI: Ta có $\\int_0^1 x^2 dx = \\left[\\frac{x^3}{3}\\right]_0^1 = \\frac{1}{3}$]
10. ĐỐI VỚI BÀI ĐỌC HIỂU / ĐIỀN TỪ (TIẾNG ANH): Nếu có một đoạn văn (passage) dùng chung cho một nhóm câu hỏi (ví dụ: "Read the following passage and mark the letter A, B, C, or D..."), hãy COPY nguyên văn đoạn văn đó và đặt vào đầu nội dung của TỪNG câu hỏi con trong nhóm đó, ngay sau thẻ [CAU N] và trước câu hỏi thực tế. Điều này giúp học sinh xem được văn cảnh khi làm từng câu hỏi riêng lẻ.
"""

_NORMALIZE_USER = (
    "Chuẩn hóa đoạn markdown sau theo EXAM-TAG-12. "
    "Chỉ trả về markdown đã chuẩn hóa, không có gì khác:\n\n{chunk}"
)


async def normalize_raw_markdown(raw_text: str) -> str:
    """Bước 1: chia nhỏ rồi gọi DeepSeek chuẩn hóa từng chunk.

    Truyền context chunk trước vào chunk sau để DeepSeek biết đang ở phần/câu nào.
    """
    chunks = _split_into_chunks(raw_text, CHUNK_SIZE)
    logger.info(f"  Normalize: {len(chunks)} chunk(s), {len(raw_text):,} chars")

    normalized_parts: list[str] = []
    prev_context = ""  # tóm tắt trạng thái cuối chunk trước

    for i, chunk in enumerate(chunks):
        logger.info(f"  DeepSeek normalize chunk {i + 1}/{len(chunks)}…")

        if prev_context:
            user_content = (
                f"CONTEXT (đoạn trước kết thúc ở): {prev_context}\n\n"
                f"Tiếp tục chuẩn hóa đoạn markdown này (KHÔNG lặp lại context, "
                f"tiếp nối đúng phần/số câu từ context):\n\n{chunk}"
            )
        else:
            user_content = _NORMALIZE_USER.format(chunk=chunk)

        try:
            resp = await deepseek.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                temperature=0,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": _NORMALIZE_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
            )
            result = resp.choices[0].message.content.strip()
            normalized_parts.append(result)

            # Trích context từ normalized output: phần cuối cùng + câu cuối cùng
            prev_context = _extract_tail_context(result)
        except Exception as e:
            logger.error(f"  Lỗi normalize chunk {i + 1}: {e}")
            normalized_parts.append(chunk)
            prev_context = ""

    return "\n\n".join(normalized_parts)


def _extract_tail_context(normalized: str) -> str:
    """Lấy thông tin cuối của đoạn đã normalize để làm context cho chunk tiếp theo."""
    # Tìm PHAN cuối cùng
    phan_matches = list(re.finditer(r'==PHAN\s*(\d+)==', normalized, re.IGNORECASE))
    last_phan = phan_matches[-1].group(0) if phan_matches else ""

    # Tìm CAU cuối cùng
    cau_matches = list(re.finditer(r'\[CAU\s+(\d+)\]', normalized, re.IGNORECASE))
    last_cau = cau_matches[-1].group(0) if cau_matches else ""

    if last_phan and last_cau:
        return f"đang ở {last_phan}, vừa xử lý xong {last_cau}"
    elif last_phan:
        return f"đang ở {last_phan}"
    return ""


def _split_into_chunks(text: str, max_size: int) -> list[str]:
    """Chia text tại ranh giới đoạn văn (\n\n) để tránh cắt giữa câu."""
    if len(text) <= max_size:
        return [text]
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para) if current else para
    if current:
        chunks.append(current.strip())
    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# BƯỚC 2 — Cắt câu bằng Python Regex
# ═══════════════════════════════════════════════════════════════════════════════

def split_normalized_text(normalized_text: str) -> list[dict]:
    """
    Bước 2: tách text đã chuẩn hóa thành danh sách câu hỏi.

    Trả về list[dict]:
        {
            "part": "part_1",           # part_1 | part_2 | part_3
            "question_index": 1,
            "raw_content": "[CAU 1]…",
            "local_image_paths": [],    # ví dụ ["images/abc.jpg"]
        }
    """
    # Tách 3 phần theo ==PHAN N==
    part_pat = re.compile(r'==PHAN\s*(\d+)==', re.IGNORECASE)
    splits = list(part_pat.finditer(normalized_text))

    # Build ordered segments
    segments: list[tuple[int, str]] = []
    for i, m in enumerate(splits):
        part_num = int(m.group(1))
        start = m.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(normalized_text)
        segments.append((part_num, normalized_text[start:end].strip()))

    # Merge: phần nào số quay về (do chunk xử lý độc lập) → gộp vào section cao nhất
    parts_map: dict[int, str] = {}
    max_seen = 0
    for (n, text) in segments:
        if n > max_seen:
            max_seen = n
            parts_map[n] = text
        else:
            # Số section bị reset (chunk 2 không biết context) → merge vào max hiện tại
            logger.debug(f"  Merge ==PHAN {n}== vào ==PHAN {max_seen}== (context reset)")
            parts_map[max_seen] = parts_map[max_seen] + "\n\n" + text

    if not parts_map:
        # Không tìm thấy tag phần → coi toàn bộ là phần 1
        logger.warning("  Không tìm thấy ==PHAN N== — xử lý toàn bộ như part_1")
        parts_map[1] = normalized_text

    questions: list[dict] = []
    for part_num in sorted(parts_map):
        qs = _split_part_into_questions(parts_map[part_num], f"part_{part_num}")
        questions.extend(qs)

    # Dedup by (part, question_index) - keep the one with longer raw_content
    deduped = {}
    for q in questions:
        key = (q["part"], q["question_index"])
        if key not in deduped or len(q["raw_content"]) > len(deduped[key]["raw_content"]):
            deduped[key] = q
    questions = [deduped[k] for k in sorted(deduped.keys())]

    logger.info(f"  Split: {len(questions)} câu từ {len(parts_map)} phần")
    return questions


def _split_part_into_questions(part_text: str, part_key: str) -> list[dict]:
    """Tách 1 phần thành các câu dựa trên tag [CAU N]."""
    cau_pat = re.compile(r'(?:^|\n)\s*\[CAU\s+(\d+)\]', re.IGNORECASE)
    matches = list(cau_pat.finditer(part_text))
    if not matches:
        return []

    questions = []
    for i, m in enumerate(matches):
        q_num = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(part_text)
        raw_content = part_text[start:end].strip()

        # Nhặt đường dẫn ảnh cục bộ MinerU (images/xxx.jpg)
        image_paths = re.findall(r'!\[[^\]]*\]\((images/[^)]+)\)', raw_content)

        questions.append({
            "part": part_key,
            "question_index": q_num,
            "raw_content": raw_content,
            "local_image_paths": image_paths,
        })
    return questions


# ═══════════════════════════════════════════════════════════════════════════════
# BƯỚC 3 — Xử lý ảnh + Trích xuất JSON dùng DeepSeek
# ═══════════════════════════════════════════════════════════════════════════════

_EXTRACT_SYSTEM = """\
Bạn là chuyên gia phân tích câu hỏi thi THPT Việt Nam (Toán, Vật Lý, Hóa Học, Lịch Sử, Tiếng Anh).
Nhiệm vụ: nhận nội dung 1 câu hỏi (đã chuẩn hóa EXAM-TAG-12) và trích xuất JSON.

Trả về DUY NHẤT 1 JSON object với các trường:
{
  "question_text": "Nội dung đề bài (giữ LaTeX và link ảnh nguyên vẹn, KHÔNG bao gồm phần [LOIGIAI:])",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_answer": "Đáp án (ví dụ: A | DSDD | 1.5 | null nếu không có [DAPAN])",
  "explanation": "Nội dung bên trong [LOIGIAI: ...] nếu có, null nếu không có tag [LOIGIAI:]",
  "topic": "Chủ đề môn học (ví dụ: Dao động cơ, Sóng cơ, Kim loại, Polime, Đọc hiểu, Từ vựng, Triều đại phong kiến, Cách mạng, Hàm số, Tích phân, Hình học không gian, Xác suất)",
  "level": "Nhận biết|Thông hiểu|Vận dụng|Vận dụng cao"
}

Lưu ý quan trọng:
- options: mảng rỗng [] nếu là câu tự luận (Phần III)
- Phần II (đúng/sai): options gồm ["a. ...", "b. ...", "c. ...", "d. ..."]
- correct_answer: lấy từ thẻ [DAPAN: X] nếu có, không thì null
- explanation: lấy TOÀN BỘ nội dung trong [LOIGIAI: ...] nếu có (giữ nguyên LaTeX), null nếu không có
- question_text: chỉ là đề bài — KHÔNG chứa [DAPAN:...], [LOIGIAI:...]\
"""

_EXTRACT_USER = "Trích xuất JSON từ câu hỏi sau:\n\n{content}"


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


def _repair_json(raw: str) -> Optional[dict]:
    """
    Parse JSON từ response DeepSeek.
    Thử 4 chiến lược theo thứ tự tăng dần độ can thiệp.
    """
    # 1. Parse thẳng
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Trích JSON object từ trong response (DeepSeek đôi khi bọc thêm text)
    m = re.search(r'\{[\s\S]+\}', raw)
    if not m:
        return None
    candidate = m.group(0)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 3. Sửa lỗi escape LaTeX phổ biến: \( \[ \{ không được escape trong JSON
    fixed = re.sub(r'(?<!\\)\\([^\\/"bfnrtu\n])', r'\\\\\1', candidate)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 4. Dùng thư viện json-repair nếu cài
    try:
        from json_repair import repair_json  # pip install json-repair
        repaired = repair_json(candidate, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
    except Exception:
        pass

    return None


async def process_single_question(
    question_dict: dict,
    exam_folder: Path,
    semaphore: asyncio.Semaphore,
    http_session: aiohttp.ClientSession,
) -> Optional[dict]:
    """Bước 3: upload ảnh + gọi DeepSeek trích xuất JSON cho 1 câu."""
    async with semaphore:
        part = question_dict["part"]
        q_num = question_dict["question_index"]
        raw_content = question_dict["raw_content"]
        image_paths = question_dict["local_image_paths"]

        # Xử lý ảnh: upload và thay đường dẫn cục bộ bằng public URL
        for local_path in image_paths:
            abs_path = exam_folder / local_path
            if abs_path.exists():
                try:
                    public_url = await _upload_image(
                        abs_path, exam_folder.name, http_session
                    )
                    raw_content = raw_content.replace(
                        f"({local_path})", f"({public_url})"
                    )
                except Exception as e:
                    logger.warning(f"  [{part}] Câu {q_num} ảnh lỗi: {e}")

        # Gọi DeepSeek với json_object mode
        try:
            resp = await deepseek.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                temperature=0,
                max_tokens=4096,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _EXTRACT_SYSTEM},
                    {"role": "user", "content": _EXTRACT_USER.format(content=raw_content)},
                ],
            )
            raw_json = resp.choices[0].message.content
        except Exception as e:
            logger.error(f"  [{part}] Câu {q_num} DeepSeek lỗi: {e}")
            return None

        # Parse + repair
        parsed = _repair_json(raw_json)
        if parsed is None:
            logger.error(
                f"  [{part}] Câu {q_num} JSON không sửa được — bỏ qua. "
                f"Raw: {raw_json[:120]!r}"
            )
            return None

        parsed["part"] = part
        parsed["question_index"] = q_num
        parsed["raw_content"] = raw_content
        return parsed


# ═══════════════════════════════════════════════════════════════════════════════
# BƯỚC 3.5 — Bổ sung đáp án từ parser_v2 (bảng đáp án cuối đề)
# ═══════════════════════════════════════════════════════════════════════════════

def _merge_parser_answers(valid_results: list[dict], raw_markdown: str) -> list[dict]:
    """
    Lấy đáp án trực tiếp từ bảng đáp án cuối đề (qua _parse_answer_table),
    không phụ thuộc vào việc parser_v2 có tìm được question boundary hay không.

    - P1 trac_nghiem / P2 dung_sai: luôn ghi đè bằng bảng (tin cậy nhất)
    - P3 tu_luan: chỉ điền khi DeepSeek chưa lấy được
    """
    from processor.parser_v2 import _parse_answer_table, _normalize, parse_exam

    # Detect mã đề từ raw markdown (giống parse_exam)
    import re as _re
    text = _normalize(raw_markdown)
    ma_de = "01"
    m = _re.search(r'[Mm][aà]\s*[dđ][eé]\s*(?:thi\s*:?\s*)?[:\s]*(\d{3,4})', text)
    if m:
        ma_de = m.group(1)[-2:]

    try:
        ans = _parse_answer_table(text, ma_de)
    except Exception as e:
        logger.warning(f"  _parse_answer_table thất bại ({e}) — giữ nguyên đáp án DeepSeek")
        return valid_results

    # Build lookup: section_int → {q_num: answer}
    # section 1 = p1, 2 = p2, 3 = p3
    lookup: dict[tuple[int, int], str] = {}
    for q_num, ans_val in ans.get("p1", {}).items():
        lookup[(1, q_num)] = str(ans_val)
    for q_num, ans_val in ans.get("p2", {}).items():
        lookup[(2, q_num)] = str(ans_val)
    for q_num, ans_val in ans.get("p3", {}).items():
        lookup[(3, q_num)] = str(ans_val)

    total_in_table = len(lookup)
    filled = missing = 0

    for data in valid_results:
        section = _part_section(data["part"])
        q_num = data["question_index"]
        table_ans = lookup.get((section, q_num))

        if table_ans is None:
            missing += 1
            continue

        q_type = _SECTION_QTYPE.get(section, "")
        current = data.get("correct_answer")

        if q_type in ("trac_nghiem", "dung_sai"):
            data["correct_answer"] = table_ans
            filled += 1
        elif not current:
            data["correct_answer"] = table_ans
            filled += 1

    logger.info(
        f"  parser_v2 merge: bảng có {total_in_table} đáp án, "
        f"điền/ghi đè {filled} câu, {missing} câu không khớp"
    )
    return valid_results


# ═══════════════════════════════════════════════════════════════════════════════
# BƯỚC 4 — Insert vào Supabase
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
    """Bước 4: insert 1 câu đã xử lý vào bảng questions."""
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

    # Tìm hoặc tạo topic
    topic_id: Optional[int] = None
    if topic_name and subject_id:
        try:
            topic_id = db.get_or_create_topic(subject_id, topic_name)
        except Exception:
            pass

    # Chuyển options list → dict
    options_dict = _options_to_dict(options_list)

    # Flags
    full_text = question_text + " ".join(options_list)
    has_formula = bool(re.search(r'\$[^$]+\$|\$\$[\s\S]+?\$\$', full_text))
    has_image = bool(re.search(r'!\[.*?\]\(.*?\)', full_text))
    has_table = bool(re.search(r'<table|\|.+\|', full_text))

    # question_number: P1 → 1-12, P2 → 101-104, P3 → 201-206
    question_number = q_num + (section - 1) * 100

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
            classification_meta={"section": section, "topic": topic_name},
        )
        return True
    except Exception as e:
        logger.error(f"  DB insert lỗi [{part}] câu {q_num}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_exam_type(title: str) -> str:
    import unicodedata as _ud
    t = _ud.normalize("NFC", title).lower()
    on_kws = (_ud.normalize("NFC", "ôn tập"), _ud.normalize("NFC", "ôn thi"), "on tap", "on thi")
    ks_kws = (_ud.normalize("NFC", "khảo sát"), "khao sat")
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


KEYWORDS = [
    r"(?i)(?:##?\s*)?LỜI\s*GIẢI\s*THAM\s*KHẢO",
    r"(?i)(?:##?\s*)?LOI\s*GIAI\s*THAM\s*KHAO",
    r"(?i)(?:##?\s*)?LỜI\s*GIẢI\s*CHI\s*TIẾT",
    r"(?i)(?:##?\s*)?LOI\s*GIAI\s*CHI\s*TIET",
    r"(?i)(?:##?\s*)?HƯỚNG\s*DẪN\s*GIẢI\s*CHI\s*TIẾT",
    r"(?i)(?:##?\s*)?HUONG\s*DAN\s*GIAI\s*CHI\s*TIET",
    r"(?i)(?:##?\s*)?HƯỚNG\s*DẪN\s*GIẢI",
    r"(?i)(?:##?\s*)?HUONG\s*DAN\s*GIAI",
    r"(?i)(?:##?\s*)?ĐÁP\s*ÁN\s*CHI\s*TIẾT",
    r"(?i)(?:##?\s*)?DAP\s*AN\s*CHI\s*TIET",
    r"(?i)(?:##?\s*)?BẢNG\s*ĐÁP\s*ÁN",
    r"(?i)(?:##?\s*)?BANG\s*DAP\s*AN",
    r"(?i)(?:##?\s*)?ĐÁP\s*ÁN\s*-\s*LỜI\s*GIẢI",
    r"(?i)(?:##?\s*)?DAP\s*AN\s*-\s*LOI\s*GIAI",
    r"(?i)LOI\s*GIAI\s*THAM\s*KHAO",
    r"(?i)LỜI\s*GIẢI\s*THAM\s*KHẢO",
    r"(?i)PHẦN\s*I\s*[-–]\s*ĐÁP\s*ÁN",
    r"(?i)PHAN\s*I\s*[-–]\s*DAP\s*AN"
]

def split_raw_markdown(text: str) -> tuple[str, str]:
    best_idx = -1
    for kw in KEYWORDS:
        matches = list(re.finditer(kw, text))
        if matches:
            idx = matches[0].start()
            if best_idx == -1 or idx < best_idx:
                best_idx = idx
    if best_idx == -1:
        # Fallback to look for "Phan I" or "PHẦN I" close to table markup
        for m in re.finditer(r"(?i)(?:##?\s*)?Phan\s*I", text):
            sub = text[m.start():m.start()+500]
            if "table" in sub or "|" in sub:
                best_idx = m.start()
                break
    if best_idx != -1:
        return text[:best_idx], text[best_idx:]
    return text, ""

async def extract_answers_and_explanations(explanations_raw_md: str) -> dict:
    if not explanations_raw_md.strip():
        return {}
    
    system_prompt = """\
Bạn là chuyên gia trích xuất đáp án và lời giải từ phần hướng dẫn giải của đề thi THPT Việt Nam (Toán, Lý, Hóa, Sử, Anh).
Nhiệm vụ: Nhận đoạn văn bản hướng dẫn giải chi tiết và trích xuất đáp án cùng lời giải chi tiết cho từng câu hỏi.

Trả về duy nhất 1 đối tượng JSON có định dạng sau:
{
  "part_1": {
    "1": {
      "answer": "A", // Đáp án của Câu 1 phần I (A, B, C hoặc D)
      "explanation": "Lời giải chi tiết của Câu 1..." // Lời giải chi tiết (giữ nguyên LaTeX và ảnh nếu có)
    },
    ...
  },
  "part_2": {
    "1": {
      "answer": "DSDS", // Đáp án của Câu 1 phần II (gồm 4 chữ cái D hoặc S tương ứng với a, b, c, d)
      "explanation": "Lời giải chi tiết cho các ý a, b, c, d..."
    },
    ...
  },
  "part_3": {
    "1": {
      "answer": "1067", // Đáp án ngắn của Câu 1 phần III (số hoặc cụm từ ngắn)
      "explanation": "Lời giải chi tiết..."
    },
    ...
  }
}

Lưu ý quan trọng:
1. Nếu đề thi không chia phần (ví dụ đề Tiếng Anh chỉ có trắc nghiệm), hãy trích xuất toàn bộ vào "part_1".
2. Giữ nguyên định dạng LaTeX ($...$, $$...$$) và ảnh (![...](...)) trong lời giải chi tiết.
3. Không tự chế câu hỏi, chỉ trích xuất từ văn bản hướng dẫn giải được cung cấp.
4. Lời giải chi tiết (explanation) cần tóm tắt ngắn gọn các bước giải chính, công thức áp dụng và kết quả, không viết quá dài dòng để tránh bị cắt cụt đầu ra JSON.
"""
    try:
        resp = await deepseek.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            temperature=0,
            max_tokens=8192,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Trích xuất đáp án và lời giải từ văn bản sau:\n\n{explanations_raw_md}"},
            ],
        )
        raw_json = resp.choices[0].message.content
        parsed = _repair_json(raw_json)
        if parsed:
            return parsed
        return json.loads(raw_json)
    except Exception as e:
        logger.error(f"  Failed to extract answers/explanations: {e}")
        return {}

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

    # ── Đọc markdown ──────────────────────────────────────────────────────────
    md_path = exam_folder / "full.md"
    if not md_path.exists():
        console.print(f"[red]  Không tìm thấy {md_path}[/]")
        return
    raw_md = md_path.read_text(encoding="utf-8")
    console.print(f"  Markdown: {len(raw_md):,} chars")

    # ── Chạy smart_parser ─────────────────────────────────────────────────────
    console.print("  [yellow]Bước 1: Chạy smart_parser (regex + heuristics)...[/]")
    from processor.smart_parser import parse_exam_file
    parsed_exams = parse_exam_file(raw_md)
    if not parsed_exams:
        console.print("[red]  smart_parser không tìm thấy đề thi nào.[/]")
        return

    exam = parsed_exams[0]
    console.print(f"  [green]smart_parser OK[/] → Phát hiện môn: {exam.subject}, Mã đề: {exam.ma_de}, Tổng: {len(exam.questions)} câu")

    # ── Bước 2: Tạo record exam ───────────────────────────────────────────────
    exam_id = _create_exam_record(exam_title, exam_year, subject_id)

    # ── Bước 3: Upload ảnh + Insert DB ────────────────────────────────────────
    console.print("  [yellow]Bước 2: Xử lý ảnh và Insert DB...[/]")
    async with aiohttp.ClientSession() as http_session:
        ok = err = 0
        for q in exam.questions:
            question_text = q.question_text
            raw_content = q.raw_text

            for local_path in q.image_paths:
                abs_path = exam_folder / local_path
                if abs_path.exists():
                    try:
                        public_url = await _upload_image(
                            abs_path, exam_folder.name, http_session
                        )
                        question_text = question_text.replace(
                            f"({local_path})", f"({public_url})"
                        )
                        raw_content = raw_content.replace(
                            f"({local_path})", f"({public_url})"
                        )
                    except Exception as e:
                        logger.warning(f"  Câu {q.index} ảnh lỗi: {e}")

            # Đổi options thành list định dạng "A. ..."
            options_list = []
            if q.options:
                for k, v in sorted(q.options.items()):
                    options_list.append(f"{k}. {v}")

            # Topic heuristic
            topic_name = "Chủ đề chung"
            text_lower = question_text.lower()
            if subject_id == 2: # Lý
                if any(w in text_lower for w in ["hạt nhân", "phóng xạ", "heli", "urani", "bohr"]):
                    topic_name = "Vật lý hạt nhân"
                elif any(w in text_lower for w in ["dao động", "chu kỳ", "tần số", "con lắc"]):
                    topic_name = "Cơ học - Dao động cơ"
                elif any(w in text_lower for w in ["nhiệt", "kelvin", "celsius", "nội năng", "đông đặc", "nóng chảy"]):
                    topic_name = "Nhiệt học"
                elif any(w in text_lower for w in ["điện xoay chiều", "suất điện động", "cuộn dây", "tụ điện"]):
                    topic_name = "Điện xoay chiều"
                elif any(w in text_lower for w in ["sóng", "phát xạ", "giao thoa"]):
                    topic_name = "Sóng cơ"
            elif subject_id == 3: # Hóa
                if any(w in text_lower for w in ["polymer", "urea", "formaldehyde", "anilin", "ester", "chất béo"]):
                    topic_name = "Hóa hữu cơ - Polymer"
                elif any(w in text_lower for w in ["kim loại", "ion", "sắt", "đồng", "điện cực"]):
                    topic_name = "Hóa vô cơ - Kim loại"

            final_data = {
                "part": f"part_{q.section}",
                "question_index": q.index,
                "question_text": question_text,
                "options": options_list,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "topic": topic_name,
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
    import unicodedata
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

    # Không có arg → liệt kê đề
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

    # Arg 1: số thứ tự hoặc keyword
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
