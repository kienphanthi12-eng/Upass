import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, correct_answer FROM questions WHERE correct_answer IS NOT NULL")
        rows = cur.fetchall()
        count = 0
        for q_id, ans in rows:
            if 'Đ' in ans or 'đ' in ans:
                new_ans = ans.replace('Đ', 'D').replace('đ', 'd').upper().strip()
                cur.execute("UPDATE questions SET correct_answer = %s WHERE id = %s", (new_ans, q_id))
                count += 1
        conn.commit()
        print(f"Normalized {count} answers containing Đ to D in database.")
