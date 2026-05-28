import sys, io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from processor.parser_v2 import _parse_answer_table, _normalize

folder = Path("C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-So-GD-An-Giang.pdf-beb0786d-163d-4ee3-8e65-373f9cca1867")
md_path = folder / "full.md"
raw_md = md_path.read_text(encoding="utf-8")
text = _normalize(raw_md)

print("Last 2000 chars of file:")
print(raw_md[-2000:])

