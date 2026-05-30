import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Find draft exams
        cur.execute("""
            SELECT id, title, ocr_job_id, status, created_at 
            FROM draft_exams 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        drafts = cur.fetchall()
        print("=== RECENT DRAFT EXAMS ===")
        for d in drafts:
            print(f"ID: {d[0]}, Title: {d[1]}, JobID: {d[2]}, Status: {d[3]}, Created: {d[4]}")
            
            # Count questions
            cur.execute("SELECT COUNT(*) FROM draft_questions WHERE draft_exam_id = %s", (d[0],))
            q_count = cur.fetchone()[0]
            print(f"  -> Question Count: {q_count}")
            
            # If JobID exists, fetch job details
            if d[2]:
                cur.execute("SELECT status, error_msg, filename, length(markdown), length(normalized_markdown) FROM ocr_jobs WHERE id = %s", (d[2],))
                job = cur.fetchone()
                if job:
                    print(f"  -> OCR Job: Status={job[0]}, Err={job[1]}, Filename={job[2]}, MarkdownLen={job[3]}, NormLen={job[4]}")
        print("==========================")
