import re
import sys
import io
from pathlib import Path

# Fix console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

MINERU_DIR = Path("C:/Users/HP/MinerU")
folders = [
    "thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Vat-Li-So-GD-Lam-Dong-.pdf-406acd9e-0fbe-4aa4-adc3-af839963a842",
    "thuvienhoclieu.com-De-thi-thu-TN-THPT-2026-mon-VAT-LI-GD-DONG-NAI.pdf-62b68da5-d3d1-409d-9000-5a57804a6474",
    "thuvienhoclieu.com-De-thi-thu-Tn-THPT-nam-2026-Vat-Li-So-GD-Ca-Mau-Lan-1.pdf-f12f691a-7409-42a1-b2fd-7f8ed19bdc63",
    "thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Hoa-So-GD-Lam-Dong-.pdf-2ddd6d08-eeef-4b2e-bd31-238b5b76f028"
]

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

def split_raw_markdown(text: str):
    best_idx = -1
    matched_keyword = ""
    for kw in KEYWORDS:
        matches = list(re.finditer(kw, text))
        if matches:
            idx = matches[0].start()
            if best_idx == -1 or idx < best_idx:
                best_idx = idx
                matched_keyword = matches[0].group(0)
    
    if best_idx == -1:
        for m in re.finditer(r"(?i)(?:##?\s*)?Phan\s*I", text):
            sub = text[m.start():m.start()+500]
            if "table" in sub or "|" in sub:
                best_idx = m.start()
                matched_keyword = "Phan I + Table"
                break
                
    if best_idx != -1:
        return text[:best_idx], text[best_idx:], matched_keyword
    return text, "", ""

for f_name in folders:
    p = MINERU_DIR / f_name / "full.md"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        q_part, a_part, kw = split_raw_markdown(text)
        print(f"File: {f_name[:65]}...")
        print(f"  Matched: {repr(kw)}")
        print(f"  Total len: {len(text):,}, Questions len: {len(q_part):,}, Answers len: {len(a_part):,}")
        if a_part:
            print(f"  First 100 chars of answers: {repr(a_part[:100])}")
        else:
            print("  [WARNING] No split found!")
        print()
