import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MINERU_DIR = Path("C:/Users/HP/MinerU")
folders = [
    "thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Vat-Li-So-GD-Lam-Dong-.pdf-406acd9e-0fbe-4aa4-adc3-af839963a842",
    "thuvienhoclieu.com-De-thi-thu-TN-THPT-2026-mon-VAT-LI-GD-DONG-NAI.pdf-62b68da5-d3d1-409d-9000-5a57804a6474",
    "thuvienhoclieu.com-De-thi-thu-Tn-THPT-nam-2026-Vat-Li-So-GD-Ca-Mau-Lan-1.pdf-f12f691a-7409-42a1-b2fd-7f8ed19bdc63",
    "thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Hoa-So-GD-Lam-Dong-.pdf-2ddd6d08-eeef-4b2e-bd31-238b5b76f028"
]

# Regex pattern for matching "PHAN I", "PHAN II", "PHAN III", etc. in raw markdown
# Support OCR typos like "PHAN I1", "PHAN I1.", "PHẦN", "Phần", etc.
SECTION_PATTERN = re.compile(
    r'(?:^|\n)\s*##?\s*(?:PHẦN|PHAN|Phần|Phan)\s+([I1Vv\d]+)',
    re.IGNORECASE
)

def split_raw_into_sections(text: str):
    matches = list(SECTION_PATTERN.finditer(text))
    if not matches:
        return [("part_1", text)]
        
    sections = []
    # If there is content before the first section heading (e.g. title, metadata)
    # append it to the first section or process it
    intro = text[:matches[0].start()].strip()
    
    for i, m in enumerate(matches):
        raw_part = m.group(1).upper()
        # Map raw Roman/digits to part number: I/1 -> 1, II/I1/2 -> 2, III/3 -> 3
        part_num = 1
        if "III" in raw_part or "3" in raw_part:
            part_num = 3
        elif "II" in raw_part or "I1" in raw_part or "2" in raw_part:
            part_num = 2
            
        start = m.start()
        end = matches[i+1].start() if i + 1 < len(matches) else len(text)
        part_text = text[start:end].strip()
        
        # If there was intro text and this is the first section, prepend intro to it
        if i == 0 and intro:
            part_text = intro + "\n\n" + part_text
            
        sections.append((f"part_{part_num}", part_text))
        
    return sections

for f_name in folders:
    p = MINERU_DIR / f_name / "full.md"
    if p.exists():
        text = p.read_text(encoding="utf-8")
        # Split explanations out first
        from test_split import split_raw_markdown
        q_part, _, _ = split_raw_markdown(text)
        
        sections = split_raw_into_sections(q_part)
        print(f"File: {f_name[:50]}...")
        for p_name, p_text in sections:
            print(f"  Section: {p_name}, len: {len(p_text):,}")
            print(f"    Snippet: {repr(p_text[:80])} ... {repr(p_text[-80:])}")
        print()
