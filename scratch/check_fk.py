import sys, io
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Check foreign keys pointing to exams
        cur.execute("""
            SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name IN ('exams', 'questions');
        """)
        print("Foreign Keys pointing to exams or questions:")
        for r in cur.fetchall():
            print(f"Table: {r[0]}, Column: {r[1]} -> Ref Table: {r[2]}, Column: {r[3]}")
            
        # Also check if there are any submissions or assignments for these exam_ids
        exam_ids = (177, 178, 184, 185, 186, 187, 188, 189, 190)
        cur.execute("SELECT COUNT(*) FROM exam_submissions WHERE exam_id IN %s", (exam_ids,))
        print("exam_submissions count:", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM assignments WHERE exam_id IN %s", (exam_ids,))
        print("assignments count:", cur.fetchone()[0])

