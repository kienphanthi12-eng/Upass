import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, title, display_title FROM exams ORDER BY id")
        rows = cur.fetchall()
        for r in rows:
            print(f"ID: {r[0]} | Title: {r[1]} | Display Title: {r[2]}")
