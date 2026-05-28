import sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Get all English exams (regardless of ocr_status)
        cur.execute("SELECT id, title, ocr_status FROM exams WHERE subject_id = 9 ORDER BY id")
        exams = cur.fetchall()
        
        print("Auditing ENGLISH questions database...")
        
        for exam_id, exam_title, ocr_status in exams:
            cur.execute("""
                SELECT id, question_number, question_type, content, options, correct_answer
                FROM questions
                WHERE exam_id = %s
                ORDER BY question_number
            """, (exam_id,))
            questions = cur.fetchall()
            
            print(f"=== {exam_title} (ID: {exam_id}, Status: {ocr_status}) ===")
            print(f"  Total questions found: {len(questions)}")
            
            # Check for missing question numbers in sequence (e.g. from 1 to 40)
            existing_nums = {q[1] for q in questions}
            missing_nums = [n for n in range(1, 41) if n not in existing_nums]
            if missing_nums:
                print(f"  Missing question numbers in sequence: {missing_nums}")
                
            issues = []
            for q_id, q_num, q_type, content, options, ans in questions:
                opts_dict = options or {}
                
                # Check for null options or options without text
                if q_type == 'trac_nghiem':
                    if not opts_dict:
                        issues.append(f"Câu {q_num}: Thiếu options")
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            issues.append(f"Câu {q_num}: Thiếu các lựa chọn: {', '.join(missing_keys)}")
                    if not ans:
                        issues.append(f"Câu {q_num}: Thiếu đáp án đúng")
                        
            if issues:
                print("  Issues:")
                for issue in issues[:10]:
                    print(f"    - {issue}")
                if len(issues) > 10:
                    print(f"    - ... and {len(issues) - 10} more issues")
            print("-" * 50)
