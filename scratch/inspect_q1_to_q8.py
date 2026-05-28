import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT question_number, content, content_raw, options, correct_answer 
            FROM questions 
            WHERE exam_id = 181 AND question_number <= 8
            ORDER BY question_number
        """)
        for r in cur.fetchall():
            print(f"\nQ{r[0]}:")
            print(f"  Content: {repr(r[1])}")
            print(f"  Raw:     {repr(r[2])}")
            print(f"  Options: {json.dumps(r[3], ensure_ascii=False)}")
            print(f"  Correct: {r[4]}")
