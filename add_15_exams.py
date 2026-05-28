"""
add_15_exams.py — Thêm 15 đề mới từ data/pdfs/ lên web UI.

Flow:
  1. Un-hide các câu sqrt đã ẩn (sau khi đã fix rendering)
  2. Lọc PDF đơn lẻ (bỏ qua "Bộ đề", "Tuyển tập", "N đề")
  3. Bỏ qua PDF đã có trong DB
  4. Với mỗi PDF mới (tối đa 15):
     a. Dùng MinerU folder sẵn có (nếu đã từng OCR) hoặc gọi MinerU API
     b. Chạy DeepSeek pipeline (bước 1-4)
     c. Auto-hide câu lỗi (quá ngắn, trac_nghiem không options)
  5. Cleanup: xóa duplicate + trim tu_luan thừa
  6. Gán city name cho đề mới
  7. Tóm tắt kết quả

Usage:
  python add_15_exams.py           # xử lý đến 15 đề mới
  python add_15_exams.py --dry     # liệt kê đề sẽ xử lý, không import
  python add_15_exams.py --max 5   # chỉ xử lý 5 đề
"""
import asyncio
import io
import re
import sys
import time
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import config
from database import db
from import_exam_deepseek import run_pipeline
from processor.ocr import MinerUClient

console = Console()

PDF_DIR   = Path("./data/pdfs")
MINERU_DIR = Path("C:/Users/HP/MinerU")
EXAM_YEAR  = 2026
TARGET_COUNT = 15  # số đề mới cần thêm

# City pool để gán display_title
CITY_POOL = [
    "Tokyo", "Kyoto", "Osaka", "Seoul", "Busan", "Singapore",
    "Bangkok", "Hanoi", "Ho Chi Minh", "Taipei", "Shanghai",
    "Beijing", "Hong Kong", "Mumbai", "Delhi", "Karachi",
    "Istanbul", "Cairo", "Lagos", "Nairobi", "Johannesburg",
    "Paris", "London", "Berlin", "Madrid", "Rome",
    "Amsterdam", "Vienna", "Prague", "Warsaw", "Budapest",
    "Athens", "Lisbon", "Brussels", "Stockholm", "Oslo",
    "Copenhagen", "Helsinki", "Dublin", "Zurich", "Geneva",
    "New York", "Los Angeles", "Chicago", "Toronto", "Vancouver",
    "Mexico City", "São Paulo", "Buenos Aires", "Lima", "Bogotá",
    "Sydney", "Melbourne", "Auckland", "Cape Town", "Casablanca",
    "Accra", "Dakar", "Addis Ababa", "Khartoum", "Riyadh",
    "Dubai", "Doha", "Muscat", "Tehran", "Islamabad",
    "Dhaka", "Colombo", "Yangon", "Phnom Penh", "Vientiane",
    "Kuala Lumpur", "Jakarta", "Manila", "Ulaanbaatar", "Almaty",
    "Tashkent", "Baku", "Tbilisi", "Yerevan", "Kiev",
    "Minsk", "Riga", "Vilnius", "Tallinn", "Bratislava",
    "Ljubljana", "Zagreb", "Sarajevo", "Belgrade", "Bucharest",
    "Sofia", "Skopje", "Tirana", "Podgorica", "Chisinau",
    "Reykjavik", "Valletta", "Monaco", "Andorra", "Luxembourg",
    "Nicosia", "Bern", "Vaduz", "San Marino", "Lismore",
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _strip_accent(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()


def is_multi_exam(pdf_name: str) -> bool:
    """Trả về True nếu PDF chứa nhiều đề (cần bỏ qua)."""
    # Kiểm tra trực tiếp ký tự Unicode Vietnamese
    # Số + "đề" → nhiều đề (vd: "20 đề", "130 đề")
    if re.search(r'\d+\s+đề', pdf_name):
        return True
    # "Bộ đề" không có tên trường cụ thể
    if 'Bộ đề' in pdf_name and 'trường' not in pdf_name:
        return True
    # "Tuyển tập"
    if 'Tuyển tập' in pdf_name:
        return True
    return False


def pdf_to_title(pdf_path: Path) -> str:
    """Chuyển đường dẫn PDF → tên đề thi (bỏ tiền tố '2026_' và '.pdf')."""
    stem = pdf_path.stem
    if stem.startswith("2026_"):
        stem = stem[len("2026_"):]
    return stem.strip()


def get_existing_db_titles() -> set[str]:
    """Lấy tập tên đề đã có trong DB (strip accent để so sánh)."""
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT title FROM exams")
            return {row[0] for row in cur.fetchall()}


def find_existing_mineru_folder(pdf_name: str) -> Path | None:
    """Tìm thư mục MinerU đã xử lý PDF này. Ưu tiên folder có nhiều nội dung nhất."""
    if not MINERU_DIR.exists():
        return None
    # PDF name = "2026_Đề ... .pdf" → tìm folder có prefix đó
    candidates = sorted([
        d for d in MINERU_DIR.iterdir()
        if d.is_dir() and d.name.startswith(pdf_name) and (d / "full.md").exists()
    ], key=lambda d: (d / "full.md").stat().st_size, reverse=True)
    return candidates[0] if candidates else None


def call_mineru_api(pdf_path: Path) -> Path | None:
    """Gọi MinerU Cloud API, lưu markdown vào MinerU/[name]-[uuid]/full.md."""
    import uuid as _uuid
    client = MinerUClient()
    console.print(f"  [yellow]→ Gọi MinerU API cho {pdf_path.name[:60]}...[/]")

    try:
        # Step 1: lấy pre-signed URL
        info = client.request_upload_url(
            pdf_path.name,
            enable_formula=True,
            enable_table=True,
            is_ocr=True,
            language="ch",
        )
        batch_id   = info["batch_id"]
        upload_url = info["upload_url"]
        console.print(f"    batch_id: {batch_id}")

        # Step 2: upload
        console.print("    Uploading...")
        client.upload_file(upload_url, str(pdf_path))

        # Step 3: poll
        console.print("    Waiting for OCR...")
        result = client.poll_batch(batch_id, timeout=600, interval=8)

        # Step 4: download markdown + images
        folder_name = f"{pdf_path.name}-{batch_id}"
        folder = MINERU_DIR / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        image_dir = folder / "images"

        markdown = client.download_markdown(result, image_dir=str(image_dir))
        md_path = folder / "full.md"
        md_path.write_text(markdown, encoding="utf-8")
        console.print(f"    [green]✓ OCR xong: {len(markdown):,} chars → {folder_name[:70]}[/]")
        return folder

    except Exception as e:
        console.print(f"    [red]MinerU thất bại: {e}[/]")
        return None


def auto_hide_buggy_questions(exam_id: int, conn) -> int:
    """Ẩn câu lỗi sau khi import. Trả về số câu đã ẩn."""
    hidden = 0
    with conn.cursor() as cur:
        # 1. Câu có content quá ngắn (< 25 ký tự) — thường là fragment/header
        cur.execute("""
            UPDATE questions
            SET is_hidden = true
            WHERE exam_id = %s
              AND is_hidden = false
              AND LENGTH(TRIM(content)) < 25
        """, (exam_id,))
        hidden += cur.rowcount

        # 2. trac_nghiem không có options (DeepSeek không extract được)
        cur.execute("""
            UPDATE questions
            SET is_hidden = true
            WHERE exam_id = %s
              AND is_hidden = false
              AND question_type = 'trac_nghiem'
              AND (options IS NULL OR options = '{}')
        """, (exam_id,))
        hidden += cur.rowcount

        # 3. tu_luan có question_number > 207 (thường là lời giải bị tách)
        cur.execute("""
            UPDATE questions
            SET is_hidden = true
            WHERE exam_id = %s
              AND is_hidden = false
              AND question_type = 'tu_luan'
              AND question_number > 207
        """, (exam_id,))
        hidden += cur.rowcount

        # 4. Câu trùng lặp (cùng question_number) — giữ lại id nhỏ nhất
        cur.execute("""
            UPDATE questions
            SET is_hidden = true
            WHERE exam_id = %s
              AND is_hidden = false
              AND id NOT IN (
                  SELECT MIN(id)
                  FROM questions
                  WHERE exam_id = %s
                  GROUP BY question_number
              )
        """, (exam_id, exam_id))
        hidden += cur.rowcount

    return hidden


def assign_city_name(exam_id: int, used_cities: set[str], conn) -> str | None:
    """Gán city name (display_title) cho đề thi mới."""
    for city in CITY_POOL:
        if city not in used_cities:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE exams SET display_title = %s WHERE id = %s",
                    (city, exam_id)
                )
            used_cities.add(city)
            return city
    return None


def get_used_cities(conn) -> set[str]:
    """Lấy tập display_title đã dùng."""
    with conn.cursor() as cur:
        cur.execute("SELECT display_title FROM exams WHERE display_title IS NOT NULL")
        return {row[0] for row in cur.fetchall()}


def un_hide_sqrt_questions(conn) -> int:
    """Un-hide câu bị ẩn vì sqrt rendering bug (chỉ áp dụng cho đề cũ id < 130).
    Không un-hide câu đã bị ẩn bởi auto_hide_buggy_questions trong pipeline mới."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE questions SET is_hidden = false
            WHERE is_hidden = true AND exam_id < 130
        """)
        return cur.rowcount


# ─── Pipeline cho 1 PDF ──────────────────────────────────────────────────────

async def process_pdf(
    pdf_path: Path,
    subject_id: int,
    used_cities: set[str],
) -> dict:
    """Xử lý 1 PDF qua full pipeline. Trả về dict kết quả."""
    title = pdf_to_title(pdf_path)

    # Kiểm tra xem đề đã tồn tại trong DB chưa (tránh duplicate khi restart)
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM exams WHERE title = %s LIMIT 1", (title,))
            if cur.fetchone():
                console.print(f"  [dim]→ Đề đã có trong DB, bỏ qua[/]")
                return {"title": title, "status": "already_exists"}

    # Tìm hoặc tạo MinerU folder
    mineru_folder = find_existing_mineru_folder(pdf_path.name)
    if mineru_folder:
        console.print(f"  [dim]→ Dùng MinerU folder sẵn có: {mineru_folder.name[:70]}[/]")
    else:
        mineru_folder = call_mineru_api(pdf_path)
        if not mineru_folder:
            return {"title": title, "status": "mineru_failed"}

    # Kiểm tra nội dung markdown có hợp lệ không
    md_path = mineru_folder / "full.md"
    md_content = md_path.read_text(encoding="utf-8")
    if len(md_content) < 500:
        return {"title": title, "status": "markdown_too_short", "md_len": len(md_content)}

    # Kiểm tra xem file có chứa nhiều đề không (heuristic: nhiều "Đề" headers)
    de_markers = len(re.findall(r'(?:^|\n)#+\s*Đề\s+\d+', md_content, re.MULTILINE))
    if de_markers >= 3:
        console.print(f"  [yellow]→ Phát hiện {de_markers} đề trong file — bỏ qua[/]")
        return {"title": title, "status": "multi_exam_detected", "markers": de_markers}

    # Chạy DeepSeek pipeline
    try:
        await run_pipeline(mineru_folder, title, EXAM_YEAR, subject_id)
    except Exception as e:
        console.print(f"  [red]Pipeline lỗi: {e}[/]")
        return {"title": title, "status": "pipeline_failed", "error": str(e)}

    # Tìm exam_id vừa tạo
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM exams WHERE title = %s ORDER BY id DESC LIMIT 1",
                (title,)
            )
            row = cur.fetchone()

        if not row:
            return {"title": title, "status": "exam_not_found_in_db"}
        exam_id = row[0]

        # Auto-hide câu lỗi
        hidden = auto_hide_buggy_questions(exam_id, conn)

        # Đếm câu hỏi hợp lệ
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM questions WHERE exam_id = %s AND is_hidden = false",
                (exam_id,)
            )
            q_count = cur.fetchone()[0]

        # Gán city name
        city = assign_city_name(exam_id, used_cities, conn)

    return {
        "title": title,
        "status": "success",
        "exam_id": exam_id,
        "q_count": q_count,
        "hidden": hidden,
        "city": city,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    args = sys.argv[1:]
    dry  = "--dry" in args
    max_new = TARGET_COUNT
    for j, a in enumerate(args):
        if a == "--max" and j + 1 < len(args):
            max_new = int(args[j + 1])
        elif a.startswith("--max="):
            max_new = int(a.split("=", 1)[1])

    console.print(Panel(
        f"[bold]Add {max_new} New Exams Pipeline[/]\n"
        f"[dim]PDF dir: {PDF_DIR}[/]",
        style="cyan",
    ))

    # ── Init DB ──────────────────────────────────────────────────────────────
    db.init_pool()
    subject_id = db.get_subject_id("TOAN")

    # ── Step 0: Un-hide sqrt questions ───────────────────────────────────────
    console.print("\n[bold]Bước 0: Un-hide câu sqrt đã ẩn[/]")
    with db.get_conn() as conn:
        unhidden = un_hide_sqrt_questions(conn)
    console.print(f"  [green]✓ Un-hid {unhidden} câu[/]")

    # ── Step 1: Lọc PDF ─────────────────────────────────────────────────────
    console.print("\n[bold]Bước 1: Lọc PDF đơn lẻ[/]")
    all_pdfs = sorted(PDF_DIR.glob("*.pdf"))
    single_pdfs = [p for p in all_pdfs if not is_multi_exam(p.name)]
    skipped = len(all_pdfs) - len(single_pdfs)
    console.print(f"  Tổng PDF: {len(all_pdfs)} | Bỏ qua multi-exam: {skipped} | Còn lại: {len(single_pdfs)}")

    # ── Step 2: Bỏ qua đề đã có DB ──────────────────────────────────────────
    console.print("\n[bold]Bước 2: Kiểm tra DB[/]")
    existing_titles = get_existing_db_titles()
    candidates = []
    for p in single_pdfs:
        title = pdf_to_title(p)
        # So sánh cả exact và strip-accent
        if title in existing_titles:
            continue
        # So sánh không dấu (phòng trường hợp encoding khác)
        if any(_strip_accent(title) == _strip_accent(t) for t in existing_titles):
            continue
        candidates.append(p)

    console.print(f"  Đã có trong DB: {len(single_pdfs) - len(candidates)} | Chưa có: {len(candidates)}")

    if not candidates:
        console.print("[green]  Tất cả đề đã được import![/]")
        return

    # Giới hạn số đề xử lý
    to_process = candidates[:max_new]
    console.print(f"  Sẽ xử lý: {len(to_process)} đề\n")

    # Hiển thị danh sách
    t = Table(show_header=True, header_style="bold dim")
    t.add_column("#",  justify="right", width=3)
    t.add_column("Tên đề", max_width=70)
    t.add_column("MinerU?", width=8)
    for i, p in enumerate(to_process, 1):
        has_mineru = "✓" if find_existing_mineru_folder(p.name) else "—"
        t.add_row(str(i), pdf_to_title(p)[:70], has_mineru)
    console.print(t)

    if dry:
        console.print("\n[dim]--dry mode: không import gì cả.[/]")
        return

    # ── Step 3: Import từng đề ───────────────────────────────────────────────
    console.print("\n[bold]Bước 3: Import đề thi[/]")
    with db.get_conn() as conn:
        used_cities = get_used_cities(conn)

    results = []
    t0 = time.time()

    for i, pdf_path in enumerate(to_process, 1):
        console.print(f"\n[bold cyan][{i}/{len(to_process)}] {pdf_to_title(pdf_path)[:65]}[/]")
        result = await process_pdf(pdf_path, subject_id, used_cities)
        results.append(result)

        if result["status"] == "success":
            console.print(
                f"  [green]✓ exam_id={result['exam_id']} | "
                f"{result['q_count']} câu | ẩn {result['hidden']} lỗi | "
                f"city={result.get('city', '?')}[/]"
            )
        else:
            console.print(f"  [red]✗ {result['status']}[/]")

    # ── Step 4: Tóm tắt ─────────────────────────────────────────────────────
    elapsed = time.time() - t0
    success  = [r for r in results if r["status"] == "success"]
    failed   = [r for r in results if r["status"] != "success"]

    console.print(f"\n{'='*70}")
    console.print(f"[bold]Kết quả: {len(success)}/{len(results)} thành công[/] | {elapsed:.0f}s")
    console.print(f"  → {len(success)} đề mới trên web: https://upass.io.vn/exams")

    if failed:
        console.print("\n[red]Đề thất bại:[/]")
        for r in failed:
            console.print(f"  • {r['title'][:60]}: {r['status']}")

    if success:
        console.print("\n[green]Đề thành công:[/]")
        t2 = Table(show_header=True, header_style="bold dim")
        t2.add_column("ID", width=5)
        t2.add_column("Tên đề", max_width=55)
        t2.add_column("City", width=18)
        t2.add_column("Câu", width=5)
        for r in success:
            t2.add_row(
                str(r["exam_id"]),
                r["title"][:55],
                r.get("city", "—"),
                str(r["q_count"]),
            )
        console.print(t2)


if __name__ == "__main__":
    asyncio.run(main())
