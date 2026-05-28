import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Check Exam 181 questions 1 to 5 including content_raw
        cur.execute("""
            SELECT id, question_number, content, content_raw, options, correct_answer 
            FROM questions 
            WHERE exam_id = 181 
            ORDER BY question_number 
            LIMIT 10
        """)
        print("=== EXAM 181 QUESTIONS RAW ===")
        for q in cur.fetchall():
            print(f"\nQuestion {q[1]} (ID: {q[0]}):")
            print(f"  Content: {repr(q[2])}")
            print(f"  Raw:     {repr(q[3])}")
            print(f"  Options: {json.dumps(q[4], ensure_ascii=False)}")
            print(f"  Correct: {q[5]}")
