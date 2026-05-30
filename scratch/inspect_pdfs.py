import os
from pathlib import Path

dgnl_dir = Path("data/dgnl")
if not dgnl_dir.exists():
    print(f"Directory {dgnl_dir} does not exist!")
    exit(1)

for f in dgnl_dir.glob("*.pdf"):
    print(f"\nFile: {f.name}")
    size = f.stat().st_size
    print(f"  Size: {size} bytes ({size / 1024:.2f} KB)")
    try:
        with open(f, "rb") as fh:
            header = fh.read(100)
            print(f"  Header bytes: {header[:30]}")
            if header.startswith(b"%PDF"):
                print("  Status: Starts with %PDF (Valid PDF header)")
            else:
                print("  Status: INVALID PDF (does not start with %PDF)")
                # Print preview of text if it looks like HTML
                try:
                    text_preview = header.decode('utf-8', errors='ignore')
                    print(f"  Text preview: {text_preview[:80]}")
                except Exception:
                    pass
    except Exception as e:
        print(f"  Error reading file: {e}")
