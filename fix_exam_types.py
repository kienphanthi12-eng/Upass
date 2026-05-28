"""Fix exam_type cho tất cả exams đã import."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

def detect_type(title: str) -> str:
    import unicodedata as _ud
    t = _ud.normalize("NFC", title).lower()
    on_kws = (_ud.normalize("NFC", "ôn tập"), _ud.normalize("NFC", "ôn thi"), "on tap", "on thi")
    ks_kws = (_ud.normalize("NFC", "khảo sát"), "khao sat")
    if any(k in t for k in on_kws):
        return "on_thi"
    if any(k in t for k in ks_kws):
        return "KS"
    return "thi_thu"

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, title FROM exams WHERE ocr_status='done'")
        rows = cur.fetchall()
        for exam_id, title in rows:
            etype = detect_type(title or '')
            cur.execute("UPDATE exams SET exam_type=%s WHERE id=%s", (etype, exam_id))
            print(f"  [{exam_id}] {(title or '')[:50]:<50} → {etype}")

print(f"\nDone: {len(rows)} exams updated.")
