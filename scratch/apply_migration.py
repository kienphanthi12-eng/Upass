import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Check if column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name='draft_questions' AND column_name='source_question_id'
            )
        """)
        exists = cur.fetchone()[0]
        if not exists:
            print("source_question_id column does not exist. Adding it now...")
            cur.execute("""
                ALTER TABLE draft_questions 
                ADD COLUMN IF NOT EXISTS source_question_id INTEGER DEFAULT NULL REFERENCES questions(id) ON DELETE SET NULL
            """)
            conn.commit()
            print("Successfully added source_question_id to draft_questions.")
        else:
            print("source_question_id column already exists.")
            
        # Verify columns of draft_questions
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'draft_questions'
        """)
        cols = cur.fetchall()
        print("\nUpdated Columns of draft_questions:")
        for col in cols:
            print(f"  {col[0]} ({col[1]})")
