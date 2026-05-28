import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Check all subjects
        cur.execute("SELECT id, name, code FROM subjects")
        subjects = cur.fetchall()
        print("--- SUBJECTS ---")
        for s in subjects:
            print(f"ID: {s[0]}, Name: {s[1]}, Code: {s[2]}")

        # Check count of exams per subject and their ocr_status
        cur.execute("""
            SELECT s.id, s.name, e.ocr_status, count(*) 
            FROM exams e 
            JOIN subjects s ON e.subject_id = s.id 
            GROUP BY s.id, s.name, e.ocr_status
            ORDER BY s.id
        """)
        counts = cur.fetchall()
        print("\n--- EXAMS COUNT PER SUBJECT & STATUS ---")
        for c in counts:
            print(f"Subject ID: {c[0]}, Name: {c[1]}, OCR Status: {c[2]}, Count: {c[3]}")
