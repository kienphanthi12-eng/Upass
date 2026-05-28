import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MINERU_DIR = Path("C:/Users/HP/MinerU")
PDF_DIR = Path("data/pdfs")

def main():
    print("=== Checking MinerU folders for English ===")
    mineru_english = []
    if MINERU_DIR.exists():
        for d in MINERU_DIR.iterdir():
            if d.is_dir() and (d / "full.md").exists():
                name_lower = d.name.lower()
                if any(w in name_lower for w in ["tieng-anh", "tieng_anh", "english", "anh"]):
                    mineru_english.append(d)
    
    print(f"Found {len(mineru_english)} English folders in MinerU:")
    for idx, d in enumerate(mineru_english, 1):
        print(f"  {idx}. {d.name}")
        
    print("\n=== Checking data/pdfs for English ===")
    pdf_english = []
    if PDF_DIR.exists():
        for f in PDF_DIR.iterdir():
            if f.is_file():
                name_lower = f.name.lower()
                if any(w in name_lower for w in ["tieng-anh", "tieng_anh", "english", "anh"]):
                    pdf_english.append(f)
                    
    print(f"Found {len(pdf_english)} English files in data/pdfs:")
    for idx, f in enumerate(pdf_english, 1):
        print(f"  {idx}. {f.name}")

if __name__ == "__main__":
    main()
