import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Check subjects in the database
        cur.execute("SELECT id, name, code FROM subjects")
        print("=== SUBJECTS IN DB ===")
        for s in cur.fetchall():
            print(f"ID: {s[0]}, Name: {s[1]}, Code: {s[2]}")

        # Check English exams
        cur.execute("""
            SELECT e.id, e.title, e.subject_id, s.name, s.code 
            FROM exams e 
            LEFT JOIN subjects s ON e.subject_id = s.id 
            WHERE e.title ILIKE '%Tieng_Anh%' OR e.title ILIKE '%Tiếng Anh%'
        """)
        print("\n=== ENGLISH EXAMS IN DB ===")
        for e in cur.fetchall():
            print(f"ID: {e[0]}, Title: {e[1][:60]}, Subject ID: {e[2]}, Subject Name: {e[3]}, Code: {e[4]}")
