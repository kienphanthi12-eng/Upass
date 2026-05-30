import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

job_id = '21993932-51b6-418a-9e10-6788acc505f2'

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT markdown, normalized_markdown FROM ocr_jobs WHERE id = %s", (job_id,))
        row = cur.fetchone()
        if row:
            markdown, norm_markdown = row
            with open('scratch/job_raw.md', 'w', encoding='utf-8') as f:
                f.write(markdown or '')
            with open('scratch/job_normalized.md', 'w', encoding='utf-8') as f:
                f.write(norm_markdown or '')
            print("Successfully wrote markdown and normalized_markdown to scratch files.")
        else:
            print("Job not found.")
