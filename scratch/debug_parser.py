import sys
import io
import re

sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

with open('C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Vat-Li-So-GD-Lam-Dong-.pdf-406acd9e-0fbe-4aa4-adc3-af839963a842/full.md', 'r', encoding='utf-8') as f:
    text = f.read()

from processor.parser_v2 import _find_ans_boundary, _normalize
text = _normalize(text)

ans_pos = _find_ans_boundary(text)
print("ans_pos:", ans_pos)
if ans_pos >= len(text):
    print("Answer boundary not found!")
    sys.exit()

ans_text = text[ans_pos:]
print("ans_text length:", len(ans_text))

table_matches = list(re.finditer(r'<table[\s\S]+?</table>', ans_text, re.I))
print("Number of tables in ans_text:", len(table_matches))
if not table_matches:
    sys.exit()

for i, tm in enumerate(table_matches):
    table_html = tm.group(0)
    print(f"\n--- Table {i+1} HTML ---")
    print(table_html[:500])
    
    rows = re.findall(r'<tr[\s\S]*?</tr>', table_html, re.I)
    print("Rows:", len(rows))
    if not rows: continue
    
    header_cells = re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', rows[0], re.I)
    header_vals = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
    print("Header values:", header_vals)
    
    is_transposed = (
        bool(header_vals) and
        re.search(r'm[aăā][^a-z]{0,3}[dđ]', header_vals[0], re.I) and
        header_vals[1:] and
        re.match(r'^[1-9]\d?$', re.sub(r'\s+', '', header_vals[1]))
    )
    print("is_transposed:", is_transposed)
    
    is_three_col = (
        len(header_vals) == 3 and
        re.search(r'm[aă][^a-z]{0,5}[dđ]', header_vals[0], re.I) and
        re.search(r'[Cc][aâ][uư]', header_vals[1], re.I)
    )
    print("is_three_col:", is_three_col)
