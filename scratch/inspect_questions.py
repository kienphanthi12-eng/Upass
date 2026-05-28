import sys, os
sys.path.insert(0, os.getcwd())
from processor.smart_parser import parse_exam_file
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

fpath = Path('C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-TN-THPT-2026-mon-VAT-LI-GD-DONG-NAI.pdf-62b68da5-d3d1-409d-9000-5a57804a6474/full.md')
raw = fpath.read_text(encoding='utf-8')
exams = parse_exam_file(raw)
exam = exams[0]

problematic = [
    (1, 9),
    (2, 2),
    (2, 3),
    (2, 4),
    (2, 6)
]

for sec, idx in problematic:
    q = next((x for x in exam.questions if x.section == sec and x.index == idx), None)
    if q:
        print(f"=== SEC {sec} Q{idx} ({q.q_type}) ===")
        print("Raw text:")
        print(q.raw_text[:400])
        print("Options:", q.options)
        print("Correct Answer:", q.correct_answer)
        print()
    else:
        print(f"=== SEC {sec} Q{idx} NOT FOUND ===")
