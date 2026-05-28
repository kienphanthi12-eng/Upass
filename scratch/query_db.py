import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()
with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.id, e.title, e.ocr_status, count(q.id) 
            FROM exams e 
            LEFT JOIN questions q ON q.exam_id = e.id 
            WHERE e.subject_id = 9 
            GROUP BY e.id, e.title, e.ocr_status
            ORDER BY e.id
        """)
        print("English exams in DB:")
        for r in cur.fetchall():
            print(f"ID: {r[0]}, Title: {r[1]}, Status: {r[2]}, Questions: {r[3]}")


