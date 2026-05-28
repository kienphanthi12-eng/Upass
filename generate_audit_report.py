import sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

REPORT_PATH = r"C:\Users\HP\.gemini\antigravity\brain\c87b3396-5c42-48d3-ac94-7b0983e034b0\data_audit_report.md"

with db.get_conn() as conn:
    with conn.cursor() as cur:
        # Get all exams with display_title
        cur.execute("SELECT id, title, display_title FROM exams WHERE ocr_status='done' ORDER BY id")
        exams = cur.fetchall()
        
        md_content = """# Báo cáo rà soát dữ liệu các đề thi trên hệ thống (Mã hóa theo Tên Thành Phố)

Báo cáo này liệt kê tình trạng dữ liệu của tất cả các đề thi đang hoạt động trên website dưới tên mã hóa (tên các thành phố). Viêc rà soát tập trung vào tính đầy đủ của các tùy chọn trả lời (options) và đáp án đúng (correct_answer) cho cả 3 phần:
- **Phần I (Trắc nghiệm)**: Cần đầy đủ 4 phương án A, B, C, D và đáp án đúng (A/B/C/D).
- **Phần II (Đúng/Sai)**: Cần đầy đủ 4 ý phụ A, B, C, D và đáp án đúng dưới dạng chuỗi 4 ký tự D/S (ví dụ: DSDS).
- **Phần III (Tự luận điền số)**: Cần có đáp án đúng (là số hoặc chuỗi số).

---

## 1. Bảng tổng hợp các đề thi có thiếu sót dữ liệu

| Tên đề thi (Mã hóa) | Tổng số câu | Thiếu ĐA Phần I (Trắc nghiệm) | Thiếu ĐA Phần II (Đúng/Sai) | Thiếu ĐA Phần III (Tự luận) | Lỗi Options (Thiếu phương án) |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
        
        no_issue_exams = []
        has_issue_exams_count = 0
        total_exams = len(exams)
        
        detail_sections = []

        for exam_id, exam_title, display_title in exams:
            # Determine the name to show
            exam_name = display_title if display_title else exam_title
            
            cur.execute("""
                SELECT id, question_number, question_type, content, options, correct_answer
                FROM questions
                WHERE exam_id = %s AND is_hidden = false
                ORDER BY question_number
            """, (exam_id,))
            questions = cur.fetchall()
            
            p1_missing_ans = 0
            p2_missing_ans = 0
            p3_missing_ans = 0
            missing_opts = 0
            
            issues = []
            for q_id, q_num, q_type, content, options, ans in questions:
                opts_dict = {}
                if options:
                    if isinstance(options, str):
                        try:
                            opts_dict = json.loads(options)
                        except:
                            issues.append(f"Câu {q_num} ({q_type}): Lỗi cấu trúc JSON của tùy chọn")
                            missing_opts += 1
                            continue
                    elif isinstance(options, dict):
                        opts_dict = options
                
                # Check by type
                if q_type == 'trac_nghiem':
                    # Check options
                    if not opts_dict:
                        issues.append(f"Câu {q_num} (Trắc nghiệm): Không có tùy chọn A, B, C, D")
                        missing_opts += 1
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            issues.append(f"Câu {q_num} (Trắc nghiệm): Thiếu phương án {', '.join(missing_keys)}")
                            missing_opts += 1
                    
                    # Check answer
                    if not ans:
                        issues.append(f"Câu {q_num} (Trắc nghiệm): Thiếu đáp án đúng")
                        p1_missing_ans += 1
                    elif ans not in ['A', 'B', 'C', 'D']:
                        issues.append(f"Câu {q_num} (Trắc nghiệm): Đáp án không hợp lệ ('{ans}')")
                        p1_missing_ans += 1
                        
                elif q_type == 'dung_sai':
                    # Check options
                    if not opts_dict:
                        issues.append(f"Câu {q_num} (Đúng/Sai): Không có 4 ý phụ A, B, C, D")
                        missing_opts += 1
                    else:
                        missing_keys = [k for k in ['A', 'B', 'C', 'D'] if k not in opts_dict or not opts_dict[k]]
                        if missing_keys:
                            issues.append(f"Câu {q_num} (Đúng/Sai): Thiếu ý phụ {', '.join(missing_keys)}")
                            missing_opts += 1
                    
                    # Check answer
                    if not ans:
                        issues.append(f"Câu {q_num} (Đúng/Sai): Thiếu đáp án đúng")
                        p2_missing_ans += 1
                    else:
                        ans_clean = ans.replace('?', '').upper()
                        if len(ans_clean) < 4 or any(c not in ['D', 'S'] for c in ans_clean):
                            issues.append(f"Câu {q_num} (Đúng/Sai): Đáp án đúng không đủ hoặc không hợp lệ ('{ans}')")
                            p2_missing_ans += 1
                            
                elif q_type == 'tu_luan':
                    # Check answer only
                    if not ans:
                        issues.append(f"Câu {q_num} (Tự luận): Thiếu đáp án đúng điền số")
                        p3_missing_ans += 1

            if p1_missing_ans > 0 or p2_missing_ans > 0 or p3_missing_ans > 0 or missing_opts > 0 or issues:
                has_issue_exams_count += 1
                md_content += f"| {exam_name} | {len(questions)} | {p1_missing_ans} | {p2_missing_ans} | {p3_missing_ans} | {missing_opts} |\n"
                
                # Create a detail block for this exam
                detail_block = f"### {exam_name} (ID: {exam_id})\n\n"
                for issue in issues:
                    detail_block += f"- {issue}\n"
                detail_sections.append(detail_block)
            else:
                no_issue_exams.append(exam_name)

        md_content += "\n---\n\n## 2. Chi tiết lỗi của từng đề thi\n\n"
        md_content += "\n".join(detail_sections)
        
        md_content += "\n---\n\n## 3. Danh sách các đề thi đầy đủ dữ kiện (Không có lỗi)\n\n"
        if no_issue_exams:
            for name in no_issue_exams:
                md_content += f"- {name}\n"
        else:
            md_content += "_Không có đề thi nào đầy đủ dữ kiện hoàn toàn._\n"
            
        md_content = f"""# Báo cáo rà soát dữ liệu đề thi (Mã hóa: Tên Thành Phố)

> [!NOTE]
> Tổng số đề thi đã OCR hoàn thành: **{total_exams}**
> Số đề thi phát hiện lỗi dữ liệu (thiếu đáp án hoặc tùy chọn): **{has_issue_exams_count}**
> Số đề thi đầy đủ dữ kiện hoàn toàn: **{len(no_issue_exams)}**

""" + md_content

        with open(REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        print(f"Report written to {REPORT_PATH}")
