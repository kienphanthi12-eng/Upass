import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

draft_exam_id = '31e64a7c-2aeb-4d17-9cce-36992a8f2a27'

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Check draft questions count
        cur.execute("SELECT COUNT(*) FROM draft_questions WHERE draft_exam_id = %s", (draft_exam_id,))
        count = cur.fetchone()[0]
        print(f"Total questions for draft {draft_exam_id}: {count}")
        
        # Are there any other draft questions in the DB?
        cur.execute("SELECT draft_exam_id, COUNT(*) FROM draft_questions GROUP BY draft_exam_id")
        group_counts = cur.fetchall()
        print("\nAll draft questions grouping by draft_exam_id:")
        for exam_id, q_count in group_counts:
            print(f"  Exam ID: {exam_id} -> Questions: {q_count}")
            
        # Check constraints or triggers on draft_questions
        # Let's inspect the database structure of draft_questions
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'draft_questions'
        """)
        cols = cur.fetchall()
        print("\nColumns of draft_questions:")
        for col in cols:
            print(f"  {col[0]} ({col[1]}) - Nullable: {col[2]}")
            
        # Let's see if there are any error logs or system messages
        cur.execute("SELECT id, status, question_count, error_msg FROM ocr_jobs WHERE id = '21993932-51b6-418a-9e10-6788acc505f2'")
        job = cur.fetchone()
        print(f"\nOCR Job Details: ID={job[0]}, Status={job[1]}, QuestionCountInJobField={job[2]}, Error={job[3]}")
