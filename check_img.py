import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
sys.path.insert(0, '.')
from preview_exam import parse_questions

norm_path = next(Path('data/processed').glob('*Thánh Tông*normalized*'))
norm = norm_path.read_text(encoding='utf-8')
qs = parse_questions(norm, Path('data/processed/images'))
p3q6 = next((q for q in qs if q['part']==3 and q['num']==6), None)
has_img = '![' in (p3q6['content'] or '')
out = f"P3 CAU 6 has_image={has_img}\n\nContent[:300]:\n{(p3q6['content'] or '')[:300]}"
Path('data/processed/img_check.txt').write_text(out, encoding='utf-8')
