import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
sys.path.insert(0, '.')
from preview_exam import parse_questions

norm = Path('data/processed/2026_Đề thi thử TN THPT 2026 môn Toán trường Lê Thánh Tông – TP HCM_normalized.md').read_text(encoding='utf-8')
qs = parse_questions(norm, Path('data/processed/images'))

lines = [f'{len(qs)} cau total']
for q in qs:
    opts = list(q['options'].keys())
    exp_preview = (q['explanation'] or '')[:60].replace('\n', ' ')
    lines.append(f"P{q['part']} CAU {q['num']}: correct={str(q['correct']):<12} opts={opts}")
    if exp_preview:
        lines.append(f"   exp: {exp_preview}")

Path('data/processed/check_parse_out.txt').write_text('\n'.join(lines), encoding='utf-8')
