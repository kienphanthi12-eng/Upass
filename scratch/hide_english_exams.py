import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Update ocr_status to 'hidden' for all English exams (subject_id = 9)
        cur.execute("UPDATE exams SET ocr_status = 'hidden' WHERE subject_id = 9")
        count = cur.rowcount
        conn.commit()
        print(f"Successfully hid {count} English exams in the database.")
