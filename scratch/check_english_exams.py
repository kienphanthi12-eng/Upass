import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Check all English exams
        cur.execute("""
            SELECT e.id, e.title, e.display_title, e.ocr_status, count(q.id) as question_count 
            FROM exams e
            LEFT JOIN questions q ON q.exam_id = e.id
            WHERE e.subject_id = 9
            GROUP BY e.id, e.title, e.display_title, e.ocr_status
            ORDER BY e.id
        """)
        exams = cur.fetchall()
        print("--- ENGLISH EXAMS ---")
        for e in exams:
            print(f"ID: {e[0]}, Title: {e[1]}, Display Title: {e[2]}, Status: {e[3]}, Question Count: {e[4]}")
