import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

draft_exam_id = '31e64a7c-2aeb-4d17-9cce-36992a8f2a27'
job_id = '21993932-51b6-418a-9e10-6788acc505f2'

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Delete draft questions just in case (should be 0 anyway)
        cur.execute("DELETE FROM draft_questions WHERE draft_exam_id = %s", (draft_exam_id,))
        print("Deleted any existing draft questions.")
        
        # Delete the empty draft exam
        cur.execute("DELETE FROM draft_exams WHERE id = %s", (draft_exam_id,))
        print(f"Deleted draft exam {draft_exam_id}.")
        
        # Set job status back to normalized
        cur.execute("""
            UPDATE ocr_jobs 
            SET status = 'normalized', error_msg = NULL, question_count = NULL, updated_at = NOW() 
            WHERE id = %s
        """, (job_id,))
        print(f"Updated OCR job {job_id} status back to 'normalized'.")
        
        conn.commit()
        print("Transaction committed successfully.")
