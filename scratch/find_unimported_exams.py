import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()
from database import db
# Helper functions copied below

MINERU_DIR = Path("C:/Users/HP/MinerU")

def list_exam_folders() -> list[Path]:
    if not MINERU_DIR.exists():
        return []
    return sorted([
        d for d in MINERU_DIR.iterdir()
        if d.is_dir() and (d / "full.md").exists()
    ])

def folder_to_title(folder: Path) -> str:
    raw = folder.name.rsplit("-", 5)[0].replace(".pdf", "")
    return raw.replace("2026_", "").strip()

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

def get_existing_titles() -> set[str]:
    try:
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT title FROM exams")
                return {row[0] for row in cur.fetchall()}
    except Exception as e:
        print(f"Error reading exams table: {e}")
        return set()

def main():
    db.init_pool()
    folders = list_exam_folders()
    existing = get_existing_titles()
    
    unimported = []
    for f in folders:
        title = folder_to_title(f)
        if title not in existing:
            subject = detect_subject_from_folder(f)
            unimported.append((f, title, subject))
            
    print(f"Total exams in MinerU: {len(folders)}")
    print(f"Already in DB: {len(existing)}")
    print(f"Unimported exams: {len(unimported)}")
    print("\n=== Unimported list by subject ===")
    
    by_subject = {}
    for f, title, subj in unimported:
        by_subject.setdefault(subj, []).append((f.name, title))
        
    for subj, list_of_exams in sorted(by_subject.items()):
        print(f"\n--- {subj} ({len(list_of_exams)} exams) ---")
        for i, (fname, title) in enumerate(list_of_exams, 1):
            print(f"  {i:2d}. {title}  [Folder: {fname[:35]}...]")

if __name__ == "__main__":
    main()
