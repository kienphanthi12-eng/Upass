import sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

REPORT_PATH = r"C:\Users\HP\.gemini\antigravity\brain\c87b3396-5c42-48d3-ac94-7b0983e034b0\detailed_question_issues.md"

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Get all exams
        cur.execute("SELECT id, title, display_title FROM exams WHERE ocr_status='done' ORDER BY id")
        exams = cur.fetchall()
        
        md = """# Danh sách chi tiết các câu hỏi thiếu hoặc lỗi dữ kiện (Mã hóa theo Tên Thành Phố)

Tài liệu này liệt kê chi tiết từng câu hỏi trong số **402 câu hỏi** bị lỗi dữ kiện hoặc thiếu đáp án trên hệ thống, phân loại theo tên mã hóa (tên các thành phố) của từng đề thi.

---

"""
        total_issues = 0
        
        for exam_id, exam_title, display_title in exams:
            exam_name = display_title if display_title else exam_title
            
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
                        q_issues.append("Không có phương án lựa chọn A, B, C, D (options = null)")
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            q_issues.append(f"Thiếu phương án lựa chọn: {', '.join(missing_keys)}")
                    
                    if not ans:
                        q_issues.append("Thiếu đáp án đúng (correct_answer = null)")
                    elif ans not in ['A', 'B', 'C', 'D']:
                        q_issues.append(f"Đáp án không hợp lệ ('{ans}')")
                        
                elif q_type == 'dung_sai':
                    if not opts_dict:
                        q_issues.append("Không có 4 ý phụ A, B, C, D (options = null)")
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            q_issues.append(f"Thiếu ý phụ: {', '.join(missing_keys)}")
                    
                    if not ans:
                        q_issues.append("Thiếu đáp án đúng")
                    else:
                        ans_clean = ans.replace('?', '').upper()
                        if len(ans_clean) < 4 or any(c not in ['D', 'S'] for c in ans_clean):
                            q_issues.append(f"Đáp án đúng không hợp lệ hoặc thiếu ký tự ('{ans}')")
                            
                elif q_type == 'tu_luan':
                    if not ans:
                        q_issues.append("Thiếu đáp án đúng (correct_answer = null)")
                
                if q_issues:
                    exam_issues.append((q_num, q_type, content, q_issues))
                    total_issues += 1
            
            if exam_issues:
                md += f"## {exam_name} (ID: {exam_id})\n\n"
                md += "| Câu số | Loại câu | Nội dung đề bài | Lỗi dữ kiện / Thiếu sót |\n"
                md += "| :---: | :--- | :--- | :--- |\n"
                for q_num, q_type, content, q_issues in exam_issues:
                    q_type_lbl = "Trắc nghiệm" if q_type == 'trac_nghiem' else "Đúng/Sai" if q_type == 'dung_sai' else "Tự luận điền số"
                    clean_content = content.replace('\n', ' ').replace('|', '\\|').strip()
                    if len(clean_content) > 100:
                        clean_content = clean_content[:97] + "..."
                    issues_str = ", ".join(q_issues)
                    md += f"| {q_num} | {q_type_lbl} | {clean_content} | {issues_str} |\n"
                md += "\n---\n\n"
                
        md += f"\n**Tổng cộng phát hiện {total_issues} câu hỏi gặp lỗi dữ kiện.**\n"
        
        with open(REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write(md)
            
        print(f"Detailed markdown report written to {REPORT_PATH}")
