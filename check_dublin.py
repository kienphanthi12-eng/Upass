import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT question_number, question_type, correct_answer 
            FROM questions 
            WHERE exam_id = 150 AND is_hidden = false
            ORDER BY question_number
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"Q: {r[0]} | Type: {r[1]} | Ans: {r[2]}")
