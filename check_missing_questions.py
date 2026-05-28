import sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Get all exams
        cur.execute("SELECT id, title FROM exams WHERE ocr_status='done' ORDER BY id")
        exams = cur.fetchall()
        
        print("Auditing questions database...")
        
        report = []
        for exam_id, exam_title in exams:
            cur.execute("""
                SELECT id, question_number, question_type, content, options, correct_answer
                FROM questions
                WHERE exam_id = %s AND is_hidden = false
                ORDER BY question_number
            """, (exam_id,))
            questions = cur.fetchall()
            
            missing_issues = []
            for q_id, q_num, q_type, content, options, ans in questions:
                # 1. Check options
                opts_dict = {}
                if options:
                    if isinstance(options, str):
                        try:
                            opts_dict = json.loads(options)
                        except:
                            missing_issues.append(f"Câu {q_num} ({q_type}): Lỗi parse options JSON")
                    elif isinstance(options, dict):
                        opts_dict = options
                
                if q_type == 'trac_nghiem':
                    if not opts_dict:
                        missing_issues.append(f"Câu {q_num}: Thiếu tùy chọn trả lời (options)")
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            missing_issues.append(f"Câu {q_num}: Thiếu các lựa chọn: {', '.join(missing_keys)}")
                    
                    if not ans:
                        missing_issues.append(f"Câu {q_num}: Thiếu đáp án đúng")
                    elif ans not in ['A', 'B', 'C', 'D']:
                        missing_issues.append(f"Câu {q_num}: Đáp án đúng không hợp lệ ('{ans}')")
                        
                elif q_type == 'dung_sai':
                    if not opts_dict:
                        missing_issues.append(f"Câu {q_num}: Thiếu 4 ý phụ (options)")
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            missing_issues.append(f"Câu {q_num}: Thiếu các ý phụ: {', '.join(missing_keys)}")
                    
                    if not ans:
                        missing_issues.append(f"Câu {q_num}: Thiếu đáp án đúng (dạng D/S)")
                    else:
                        ans_clean = ans.replace('?', '').upper()
                        if len(ans_clean) < 4 or any(c not in ['D', 'S'] for c in ans_clean):
                            missing_issues.append(f"Câu {q_num}: Đáp án đúng không đủ hoặc không hợp lệ ('{ans}')")
                            
                elif q_type == 'tu_luan':
                    # For fill-in-the-blank / essay, options are usually null or empty, which is normal.
                    # But correct_answer is required
                    if not ans:
                        missing_issues.append(f"Câu {q_num}: Thiếu đáp án đúng (tự luận điền số)")
            
            if missing_issues:
                report.append((exam_title, missing_issues))

        print(f"\nAudit complete. Found {len(report)} exams with data issues.\n")
        for title, issues in report:
            print(f"=== {title} ===")
            for issue in issues:
                print(f"  - {issue}")
            print()
