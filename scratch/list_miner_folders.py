import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


MINERU_DIR = Path("C:/Users/HP/MinerU")

def list_exam_folders() -> list[Path]:
    if not MINERU_DIR.exists():
        print(f"Directory not found: {MINERU_DIR}")
        return []
    return sorted([
        d for d in MINERU_DIR.iterdir()
        if d.is_dir() and (d / "full.md").exists()
    ])

def main():
    folders = list_exam_folders()
    print(f"Total folders with full.md: {len(folders)}")
    for i, folder in enumerate(folders, 1):
        name_lower = folder.name.lower()
        subject = "OTHER"
        if any(w in name_lower for w in ["vat-li", "vat-ly", "vat_li", "vat_ly"]):
            subject = "LY"
        elif any(w in name_lower for w in ["hoa-hoc", "hoa_hoc", "hoa"]):
            subject = "HOA"
        elif any(w in name_lower for w in ["tieng-anh", "tieng_anh", "english", "anh"]):
            subject = "ANH"
        elif any(w in name_lower for w in ["lich-su", "lich_su", "su"]):
            subject = "SU"
        elif any(w in name_lower for w in ["toan"]):
            subject = "TOAN"
        
        # Look for images and size of full.md
        full_md = folder / "full.md"
        size_kb = full_md.stat().st_size / 1024 if full_md.exists() else 0
        print(f"{i:02d}. Folder: {folder.name} | Subject: {subject} | Size: {size_kb:.1f} KB")

if __name__ == "__main__":
    main()
