import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()
from database import db

def main():
    db.init_pool()
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, subject_id, exam_type, ocr_status, 
                       (SELECT COUNT(*) FROM questions WHERE exam_id = exams.id) as q_count
                FROM exams
                ORDER BY id DESC
                LIMIT 15
            """)
            rows = cur.fetchall()
            print("=== Last 15 Exams in DB ===")
            for row in rows:
                print(f"ID: {row[0]} | Qs: {row[5]} | Subject: {row[2]} | Title: {row[1]}")

if __name__ == "__main__":
    main()
