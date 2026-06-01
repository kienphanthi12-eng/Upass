"""
processor/detect_azota.py — Helper to detect format and subject of a DOCX or PDF file.
Usage:
  python processor/detect_azota.py <file_path>
Output:
  JSON string with {"is_azota": bool, "subject": "TOAN|LY|...", "diagnostics": dict}
"""
import os
import sys
import json
from pathlib import Path

# Adjust sys.path to import from sibling modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Prevent Windows terminal Unicode errors
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"is_azota": False, "subject": "UNKNOWN", "error": "Missing file_path"}))
        return

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(json.dumps({"is_azota": False, "subject": "UNKNOWN", "error": f"File not found: {file_path}"}))
        return

    ext = file_path.suffix.lower()
    is_azota = False
    subject = "UNKNOWN"
    diag = {}

    try:
        if ext == ".docx":
            from processor.azota_parser import is_azota_format, extract_metadata
            from docx import Document
            is_azota, diag = is_azota_format(str(file_path))
            if is_azota:
                try:
                    doc = Document(str(file_path))
                    header_text = "\n".join(p.text for p in doc.paragraphs[:40])
                    meta = extract_metadata(header_text)
                    subject = meta.get("subject", "UNKNOWN")
                except Exception as e:
                    diag["subject_error"] = str(e)
        elif ext == ".pdf":
            from processor.azota_pdf_parser import is_azota_pdf, _extract_lines
            from processor.smart_parser import extract_metadata
            import fitz
            is_azota, diag = is_azota_pdf(str(file_path))
            if is_azota:
                try:
                    doc = fitz.open(str(file_path))
                    lines = _extract_lines(doc)
                    full_head = "\n".join(l.text for l in lines[:60])
                    meta = extract_metadata(full_head)
                    subject = meta.get("subject", "UNKNOWN")
                    doc.close()
                except Exception as e:
                    diag["subject_error"] = str(e)
        else:
            diag["error"] = f"Unsupported extension: {ext}"

    except Exception as e:
        diag["error"] = str(e)

    print(json.dumps({
        "is_azota": is_azota,
        "subject": subject,
        "diagnostics": diag
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
