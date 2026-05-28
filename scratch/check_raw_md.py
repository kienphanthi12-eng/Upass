import sys, io, os
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MINERU_DIR = Path("C:/Users/HP/MinerU")
# Find the folder matching Tay Ninh English exam
target_folder = None
for d in MINERU_DIR.iterdir():
    if d.is_dir() and "tay_ninh" in d.name.lower() and "tieng_anh" in d.name.lower():
        target_folder = d
        break

if target_folder:
    print(f"Found folder: {target_folder.name}")
    md_file = target_folder / "full.md"
    if md_file.exists():
        text = md_file.read_text(encoding="utf-8")
        print("\n=== FIRST 8000 CHARACTERS OF MD ===")
        print(text[:8000])
    else:
        print("full.md not found in folder.")
else:
    print("Could not find folder for Tay Ninh English exam.")
