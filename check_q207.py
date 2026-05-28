import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Check q207 for Barcelona (105)
        cur.execute("""
            SELECT q.exam_id, e.display_title, q.question_number, q.content, q.correct_answer 
            FROM questions q JOIN exams e ON q.exam_id = e.id
            WHERE q.question_number = 207 AND q.is_hidden = false
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"Exam: {r[1]} (ID: {r[0]}) | Q: {r[2]} | Ans: {r[4]}")
            print(f"Content: {r[3][:150]}...")
            print("-" * 50)
