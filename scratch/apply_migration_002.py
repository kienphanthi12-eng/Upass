import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        print("Running migration 002...")
        cur.execute("ALTER TABLE draft_questions ADD COLUMN IF NOT EXISTS explanation TEXT;")
        cur.execute("ALTER TABLE draft_questions ADD COLUMN IF NOT EXISTS needs_review BOOLEAN DEFAULT false;")
        cur.execute("ALTER TABLE draft_questions ADD COLUMN IF NOT EXISTS review_reason TEXT;")
        conn.commit()
        print("Migration 002 run successfully.")
        
        # Verify columns of draft_questions
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'draft_questions'
        """)
        cols = cur.fetchall()
        print("\nColumns of draft_questions after migration:")
        for col in cols:
            print(f"  {col[0]} ({col[1]})")
