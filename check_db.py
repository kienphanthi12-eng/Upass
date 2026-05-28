"""Kiểm tra chất lượng dữ liệu DB sau khi import."""
import sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM exams WHERE ocr_status='done'")
        nexams = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM questions")
        nq = cur.fetchone()[0]

        cur.execute("SELECT question_type, COUNT(*) FROM questions GROUP BY question_type ORDER BY question_type")
        types = cur.fetchall()

        cur.execute("SELECT level, COUNT(*) FROM questions WHERE level IS NOT NULL AND level!='' GROUP BY level ORDER BY level")
        levels = cur.fetchall()

        cur.execute("""SELECT e.title, COUNT(q.id) as n,
                              SUM(CASE WHEN q.question_type='trac_nghiem' THEN 1 ELSE 0 END) as p1,
                              SUM(CASE WHEN q.question_type='dung_sai' THEN 1 ELSE 0 END) as p2,
                              SUM(CASE WHEN q.question_type='tu_luan' THEN 1 ELSE 0 END) as p3,
                              SUM(CASE WHEN q.correct_answer IS NOT NULL THEN 1 ELSE 0 END) as has_ans,
                              SUM(CASE WHEN q.options IS NOT NULL THEN 1 ELSE 0 END) as has_opts
                       FROM exams e JOIN questions q ON e.id=q.exam_id
                       WHERE e.ocr_status='done'
                       GROUP BY e.id, e.title ORDER BY e.id""")
        per_exam = cur.fetchall()

        # Sample question with LaTeX
        cur.execute("""SELECT content, options, correct_answer, level, question_type
                       FROM questions WHERE has_formula=true AND question_type='trac_nghiem'
                       AND options IS NOT NULL ORDER BY random() LIMIT 1""")
        sample = cur.fetchone()

        # Check images
        cur.execute("SELECT COUNT(*) FROM questions WHERE has_image=true")
        n_img = cur.fetchone()[0]

print(f"=== DB Summary ===")
print(f"Exams (done): {nexams}")
print(f"Questions total: {nq}")
print(f"Types: {dict(types)}")
print(f"Levels: {dict(levels)}")
print(f"Questions with images: {n_img}")

print(f"\n=== Per-exam breakdown ===")
print(f"{'Title':<55} {'Total':>5} {'P1':>3} {'P2':>3} {'P3':>3} {'Ans':>4} {'Opts':>4}")
for row in per_exam:
    title, n, p1, p2, p3, ans, opts = row
    title_s = (title or '')[:52]
    print(f"{title_s:<55} {n:>5} {p1:>3} {p2:>3} {p3:>3} {ans:>4} {opts:>4}")

if sample:
    content, options, ans, level, qtype = sample
    print(f"\n=== Sample câu trac_nghiem có LaTeX ===")
    print(f"Content (100c): {content[:120]}")
    opts = options if isinstance(options, dict) else json.loads(options) if options else None
    if opts:
        for k, v in list(opts.items())[:2]:
            print(f"  [{k}]: {str(v)[:60]}")
    print(f"Answer: {ans} | Level: {level}")
