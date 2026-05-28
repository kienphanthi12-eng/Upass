"""
run_deepseek_all.py — Batch runner: xử lý tất cả 20 đề từ C:/Users/HP/MinerU
bằng pipeline DeepSeek-V3 (import_exam_deepseek.py).

Tính năng:
  - Tự động phát hiện tất cả thư mục có full.md trong MINERU_DIR
  - Bỏ qua đề đã có trong DB (kiểm tra theo title)
  - Xử lý tuần tự, mỗi đề chạy async pipeline riêng
  - Resume: --skip N (bắt đầu từ đề thứ N), --only "keyword"
  - Log tóm tắt cuối cùng

Usage:
  python run_deepseek_all.py              # tất cả 20 đề
  python run_deepseek_all.py --dry        # chỉ liệt kê
  python run_deepseek_all.py --skip 5    # bắt đầu từ đề thứ 5
  python run_deepseek_all.py --only "Cau Giay"  # chỉ đề khớp keyword
  python run_deepseek_all.py --force     # import lại kể cả đề đã có trong DB
"""
import asyncio
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn

import config
from database import db
from import_exam_deepseek import run_pipeline

console = Console()

MINERU_DIR = Path("C:/Users/HP/MinerU")
EXAM_YEAR = 2026


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _strip_accent(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()


def list_exam_folders() -> list[Path]:
    """Trả về tất cả thư mục MinerU có file full.md, sắp xếp theo tên."""
    if not MINERU_DIR.exists():
        console.print(f"[red]Không tìm thấy thư mục MinerU: {MINERU_DIR}[/]")
        return []
    return sorted([
        d for d in MINERU_DIR.iterdir()
        if d.is_dir() and (d / "full.md").exists()
    ])


def folder_to_title(folder: Path) -> str:
    """Chuyển tên thư mục MinerU → tên đề thi ngắn gọn."""
    raw = folder.name.rsplit("-", 5)[0].replace(".pdf", "")
    return raw.replace("2026_", "").strip()


def get_existing_titles() -> set[str]:
    """Lấy tập hợp tên đề đã có trong DB."""
    try:
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT title FROM exams")
                return {row[0] for row in cur.fetchall()}
    except Exception as e:
        console.print(f"[yellow]Cảnh báo: không lấy được danh sách DB ({e})[/]")
        return set()


# ─── Main logic ───────────────────────────────────────────────────────────────

def detect_subject_from_folder(folder: Path) -> str:
    name_lower = folder.name.lower()
    if any(w in name_lower for w in ["vat-li", "vat-ly", "vat_li", "vat_ly"]):
        return "LY"
    if any(w in name_lower for w in ["hoa-hoc", "hoa_hoc", "hoa"]):
        return "HOA"
    if any(w in name_lower for w in ["tieng-anh", "tieng_anh", "english", "anh"]):
        return "ANH"
    if any(w in name_lower for w in ["lich-su", "lich_su", "su"]):
        return "SU"
    return "TOAN"


async def process_all(
    folders: list[Path],
    force: bool = False,
) -> dict:
    """Xử lý tuần tự từng đề, trả về dict thống kê."""
    existing = get_existing_titles() if not force else set()
    total = len(folders)
    results = {"success": [], "skipped": [], "failed": []}

    for i, folder in enumerate(folders, 1):
        title = folder_to_title(folder)
        subject_code = detect_subject_from_folder(folder)
        subject_id = db.get_subject_id(subject_code)

        # Kiểm tra đã import chưa
        if title in existing and not force:
            console.print(f"[{i:2}/{total}] [dim]Bỏ qua (đã có): {title}[/]")
            results["skipped"].append(title)
            continue

        console.print(f"\n[bold cyan][{i:2}/{total}][/] {title} ({subject_code})")
        t_start = time.time()
        try:
            await run_pipeline(folder, title, EXAM_YEAR, subject_id)
            elapsed = time.time() - t_start
            console.print(f"  [green]✓ Hoàn tất trong {elapsed:.1f}s[/]")
            results["success"].append(title)
            existing.add(title)   # <-- fix: ngăn duplicate trong cùng 1 lần chạy
        except Exception as e:
            elapsed = time.time() - t_start
            console.print(f"  [red]✗ Lỗi sau {elapsed:.1f}s: {e}[/]")
            import traceback
            traceback.print_exc()
            results["failed"].append((title, str(e)))

    return results


def print_summary(results: dict, total_time: float) -> None:
    """In bảng tóm tắt cuối cùng."""
    console.print()

    t = Table(show_header=True, header_style="bold")
    t.add_column("Trạng thái", width=12)
    t.add_column("Số lượng", justify="right", width=8)

    n_ok = len(results["success"])
    n_skip = len(results["skipped"])
    n_fail = len(results["failed"])

    t.add_row("[green]Thành công[/]", f"[green]{n_ok}[/]")
    t.add_row("[dim]Bỏ qua[/]",       f"[dim]{n_skip}[/]")
    t.add_row("[red]Lỗi[/]",          f"[red]{n_fail}[/]" if n_fail else "0")
    console.print(t)

    if results["failed"]:
        console.print("\n[red]Danh sách đề lỗi:[/]")
        for title, err in results["failed"]:
            console.print(f"  • {title}: {err[:80]}")

    mins, secs = divmod(int(total_time), 60)
    console.print(f"\n[dim]Tổng thời gian: {mins}m{secs:02d}s[/]")
    console.print("[dim]Web: http://localhost:3000/exams[/]")


def main() -> None:
    args = sys.argv[1:]
    dry   = "--dry" in args
    force = "--force" in args

    # --skip N
    skip = 0
    for j, a in enumerate(args):
        if a == "--skip" and j + 1 < len(args):
            skip = int(args[j + 1]) - 1
        elif a.startswith("--skip="):
            skip = int(a.split("=", 1)[1]) - 1

    # --only "keyword"
    only_kw: str | None = None
    for j, a in enumerate(args):
        if a == "--only" and j + 1 < len(args):
            only_kw = args[j + 1]
        elif a.startswith("--only="):
            only_kw = a.split("=", 1)[1]

    # Tìm tất cả đề
    all_folders = list_exam_folders()
    if not all_folders:
        return

    # Áp dụng --only
    if only_kw:
        kw_norm = _strip_accent(only_kw)
        all_folders = [
            f for f in all_folders
            if kw_norm in _strip_accent(folder_to_title(f))
        ]
        if not all_folders:
            console.print(f"[red]Không tìm thấy đề nào khớp '{only_kw}'[/]")
            return

    # Áp dụng --skip
    folders = all_folders[skip:]
    total = len(all_folders)

    # Hiển thị danh sách
    console.print(Panel(
        f"[bold]Batch DeepSeek Pipeline — {len(folders)} đề cần xử lý[/]\n"
        f"[dim]Thư mục: {MINERU_DIR}[/]\n"
        + (f"[dim]Bắt đầu từ đề thứ {skip+1}[/]\n" if skip else "")
        + (f"[dim]Lọc: '{only_kw}'[/]\n" if only_kw else "")
        + (f"[yellow]--force: import lại kể cả đề đã có trong DB[/]" if force else ""),
        style="cyan",
    ))

    t = Table(show_header=True, header_style="bold dim")
    t.add_column("#", justify="right", width=3)
    t.add_column("Tên đề thi", max_width=70)
    for i, f in enumerate(folders, skip + 1):
        t.add_row(str(i), folder_to_title(f))
    console.print(t)

    if dry:
        console.print("\n[dim]--dry mode: không import gì cả.[/]")
        return

    # Init DB
    db.init_pool()
    # Chạy pipeline
    t0 = time.time()
    results = asyncio.run(process_all(folders, force=force))
    total_time = time.time() - t0

    print_summary(results, total_time)


if __name__ == "__main__":
    main()
