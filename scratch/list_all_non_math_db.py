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
                SELECT e.id, e.title, e.subject_id, s.name, s.code,
                       (SELECT COUNT(*) FROM questions WHERE exam_id = e.id) as q_count
                FROM exams e
                JOIN subjects s ON e.subject_id = s.id
                WHERE s.code != 'TOAN'
                ORDER BY e.id DESC
            """)
            rows = cur.fetchall()
            print("=== Non-Toán Exams in DB ===")
            for r in rows:
                print(f"ID: {r[0]} | Code: {r[4]} | Subject: {r[3]} | Qs: {r[5]} | Title: {r[1]}")

if __name__ == "__main__":
    main()
