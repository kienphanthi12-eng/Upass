import sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, title FROM exams WHERE ocr_status='done' ORDER BY id")
        exams = cur.fetchall()
        
        total_questions_with_issues = 0
        
        for exam_id, exam_title in exams:
            cur.execute("""
                SELECT id, question_number, question_type, content, options, correct_answer
                FROM questions
                WHERE exam_id = %s AND is_hidden = false
                ORDER BY question_number
            """, (exam_id,))
            questions = cur.fetchall()
            
            exam_issues = []
            for q_id, q_num, q_type, content, options, ans in questions:
                opts_dict = {}
                if options:
                    if isinstance(options, str):
                        try:
                            opts_dict = json.loads(options)
                        except:
                            opts_dict = None
                    elif isinstance(options, dict):
                        opts_dict = options
                
                q_issues = []
                
                if q_type == 'trac_nghiem':
                    if not opts_dict:
                        q_issues.append("Không có các phương án lựa chọn A, B, C, D (options = null/empty)")
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            q_issues.append(f"Thiếu phương án: {', '.join(missing_keys)}")
                    
                    if not ans:
                        q_issues.append("Thiếu đáp án đúng (correct_answer = null)")
                    elif ans not in ['A', 'B', 'C', 'D']:
                        q_issues.append(f"Đáp án không hợp lệ ('{ans}')")
                        
                elif q_type == 'dung_sai':
                    if not opts_dict:
                        q_issues.append("Không có 4 ý phụ A, B, C, D (options = null/empty)")
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            q_issues.append(f"Thiếu ý phụ: {', '.join(missing_keys)}")
                    
                    if not ans:
                        q_issues.append("Thiếu đáp án đúng")
                    else:
                        ans_clean = ans.replace('?', '').upper()
                        if len(ans_clean) < 4 or any(c not in ['D', 'S'] for c in ans_clean):
                            q_issues.append(f"Đáp án đúng không hợp lệ hoặc thiếu ký tự ('{ans}', yêu cầu chuỗi 4 ký tự D/S)")
                            
                elif q_type == 'tu_luan':
                    if not ans:
                        q_issues.append("Thiếu đáp án đúng điền số (correct_answer = null)")
                
                if q_issues:
                    exam_issues.append((q_num, q_type, content, q_issues))
                    total_questions_with_issues += 1
            
            if exam_issues:
                print(f"=== {exam_title} ===")
                for q_num, q_type, content, q_issues in exam_issues:
                    # Clean content preview
                    clean_content = content.replace('\n', ' ').strip()
                    if len(clean_content) > 80:
                        clean_content = clean_content[:77] + "..."
                    
                    issues_str = "; ".join(q_issues)
                    print(f"  * Câu {q_num} ({q_type}) [{clean_content}]: {issues_str}")
                print()
                
        print(f"Tổng cộng có {total_questions_with_issues} câu hỏi bị thiếu hoặc lỗi dữ kiện.")
