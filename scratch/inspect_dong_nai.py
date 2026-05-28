import re
from pathlib import Path
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

fpath = Path('C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-TN-THPT-2026-mon-VAT-LI-GD-DONG-NAI.pdf-62b68da5-d3d1-409d-9000-5a57804a6474/full.md')
raw = fpath.read_text(encoding='utf-8')

print("=== PART MATCHES ===")
for i, line in enumerate(raw.split('\n'), 1):
    if re.search(r'ph[aâ]n\s*(i1|ii|iii|1|2|3|i|v)', line, re.I):
        print(f"Line {i}: {line.strip()}")

print("\n=== CAU MATCHES ===")
for i, line in enumerate(raw.split('\n'), 1):
    if re.search(r'\b[Cc][aâ][uư]?\s*\d+', line):
        print(f"Line {i}: {line.strip()[:100]}")
