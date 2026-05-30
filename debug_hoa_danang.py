"""Debug HOA Da Nang parsing"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from import_exam_docx import parse_docx_questions

_, ans, qs = parse_docx_questions(
    'data/pdfs/thuvienhoclieu.com-De-thi-thu-TN-THPT-nam-2026-mon-HOA-So-GD-Da-Nang-lan-1.docx'
)
print(f'Total: {len(qs)} questions')
for q in qs:
    print(f"sec={q['section']} num={q['number']:3} opts={len(q.get('opts',{}))} content={repr(q['content'][:70])}")
print(f"\nAnswers: I={len(ans['I'])} II={len(ans['II'])} III={len(ans['III'])}")
