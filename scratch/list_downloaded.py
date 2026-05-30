import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
from pathlib import Path

metadata_file = Path("data/dgnl_metadata.json")
if not metadata_file.exists():
    print("Metadata file does not exist!")
    exit(1)

with open(metadata_file, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total exams: {len(data)}")
for i, item in enumerate(data, 1):
    print(f"{i:2d}. [{item['exam_type']}] ({item['year']}) {item['title']}")
    print(f"    Path: {item['file_path']}")
    print(f"    Size: {item.get('file_size_bytes', 0) / 1024:.1f} KB")
