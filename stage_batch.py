"""
stage_batch.py — Chuyen flat .md files tu MinerU batch export
thanh cau truc folder/full.md ma run_deepseek_all.py can.

Cach dung:
  python stage_batch.py              # stage batch moi nhat
  python stage_batch.py --dry        # chi liet ke, khong tao folder
"""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import re
import shutil
from pathlib import Path

MINERU_DIR   = Path("C:/Users/HP/MinerU")
BATCH_PARENT = MINERU_DIR / "batch_download"

# UUID pattern
UUID_RE = re.compile(r"_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$")


def find_latest_batch() -> Path | None:
    """Tìm thư mục batch export mới nhất."""
    batches = sorted(BATCH_PARENT.glob("MinerU_Batch_Export_*"))
    return batches[-1] if batches else None


def stage_batch(batch_dir: Path, dry: bool = False) -> list[Path]:
    """Stage tất cả .md files → MINERU_DIR/[name]/full.md. Trả về danh sách folders mới."""
    md_files = sorted(batch_dir.glob("MinerU_markdown_*.md"))
    print(f"Tìm thấy {len(md_files)} file trong {batch_dir.name}")

    staged: list[Path] = []
    skipped = 0

    for md_file in md_files:
        stem = md_file.stem  # e.g. MinerU_markdown_2026_[title].pdf_[UUID]

        # Strip prefix
        if stem.startswith("MinerU_markdown_"):
            stem = stem[len("MinerU_markdown_"):]

        # Tách UUID khỏi cuối
        m = UUID_RE.search(stem)
        if not m:
            print(f"  [WARN] Không tìm thấy UUID trong: {md_file.name}")
            continue

        uuid     = m.group(1)
        pdf_name = stem[: m.start()]        # e.g. "2026_[title].pdf"
        folder_name = f"{pdf_name}-{uuid}"  # e.g. "2026_[title].pdf-[UUID]"
        folder = MINERU_DIR / folder_name
        dest   = folder / "full.md"

        if dest.exists():
            print(f"  [skip] Đã tồn tại: {folder_name[:70]}")
            skipped += 1
            continue

        print(f"  {'[dry]' if dry else '[+]'} {folder_name[:80]}")
        if not dry:
            folder.mkdir(exist_ok=True)
            shutil.copy2(md_file, dest)
            staged.append(folder)

    print(f"\nKết quả: {len(staged)} staged, {skipped} bỏ qua (đã tồn tại)")
    return staged


if __name__ == "__main__":
    dry = "--dry" in sys.argv

    batch = find_latest_batch()
    if not batch:
        print("Không tìm thấy batch export trong", BATCH_PARENT)
        sys.exit(1)

    print(f"Batch: {batch.name}\n")
    stage_batch(batch, dry=dry)
