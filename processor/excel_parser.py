import sys
import os
import json
import openpyxl

# Set encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def parse_excel(file_path):
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    rows = []
    for r in ws.iter_rows(values_only=True):
        if any(r): # skip entirely empty rows
            rows.append(r)

    if not rows:
        return {"error": "Bảng tính trống"}

    # Clean headers
    headers = [str(cell).strip().lower() if cell is not None else "" for cell in rows[0]]

    # Detect format: is it an offline answer key? (Contains "mã đề", "câu", "đáp án")
    has_ma_de = any("mã" in h or "code" in h for h in headers)
    
    if has_ma_de:
        # Format: Offline Answer Key
        # Find column indices
        col_ma = -1
        col_cau = -1
        col_ans = -1

        for i, h in enumerate(headers):
            if "mã" in h or "code" in h:
                col_ma = i
            elif "câu" in h or "số" in h or "number" in h or "q" == h:
                col_cau = i
            elif "đáp" in h or "ans" in h or "key" in h:
                col_ans = i

        # Fallbacks if headers not detected
        if col_ma == -1: col_ma = 0
        if col_cau == -1: col_cau = 1
        if col_ans == -1: col_ans = 2

        keys = []
        for r in rows[1:]:
            ma_de = str(r[col_ma]).strip() if len(r) > col_ma and r[col_ma] is not None else ""
            cau = str(r[col_cau]).strip() if len(r) > col_cau and r[col_cau] is not None else ""
            ans = str(r[col_ans]).strip() if len(r) > col_ans and r[col_ans] is not None else ""
            
            if ma_de or cau or ans:
                keys.append({
                    "ma_de": ma_de,
                    "question_number": int(float(cau)) if cau.replace('.','',1).isdigit() else cau,
                    "correct_answer": ans.upper()
                })
        
        return {
            "type": "offline_answer_key",
            "data": keys
        }

    else:
        # Format: Question List
        # Columns: Question, Option A, B, C, D, Answer, Topic, Difficulty
        col_content = -1
        col_a, col_b, col_c, col_d = -1, -1, -1, -1
        col_ans = -1
        col_topic = -1
        col_diff = -1
        col_num = -1

        for i, h in enumerate(headers):
            if "hỏi" in h or "nội dung" in h or "content" in h or "question" in h:
                col_content = i
            elif "a" == h or "phương án a" in h or "option a" in h:
                col_a = i
            elif "b" == h or "phương án b" in h or "option b" in h:
                col_b = i
            elif "c" == h or "phương án c" in h or "option c" in h:
                col_c = i
            elif "d" == h or "phương án d" in h or "option d" in h:
                col_d = i
            elif "đáp án" in h or "answer" in h or "key" in h:
                col_ans = i
            elif "chủ đề" in h or "topic" in h:
                col_topic = i
            elif "độ khó" in h or "khó" in h or "difficulty" in h or "mức độ" in h:
                col_diff = i
            elif "câu" == h or "số" == h or "stt" in h:
                col_num = i

        # Fallbacks if columns not named precisely
        if col_content == -1: col_content = 0
        if col_a == -1: col_a = 1
        if col_b == -1: col_b = 2
        if col_c == -1: col_c = 3
        if col_d == -1: col_d = 4
        if col_ans == -1: col_ans = 5

        questions = []
        for idx, r in enumerate(rows[1:], 1):
            content = str(r[col_content]).strip() if len(r) > col_content and r[col_content] is not None else ""
            if not content:
                continue

            opt_a = str(r[col_a]).strip() if col_a != -1 and len(r) > col_a and r[col_a] is not None else ""
            opt_b = str(r[col_b]).strip() if col_b != -1 and len(r) > col_b and r[col_b] is not None else ""
            opt_c = str(r[col_c]).strip() if col_c != -1 and len(r) > col_c and r[col_c] is not None else ""
            opt_d = str(r[col_d]).strip() if col_d != -1 and len(r) > col_d and r[col_d] is not None else ""
            
            ans = str(r[col_ans]).strip() if col_ans != -1 and len(r) > col_ans and r[col_ans] is not None else ""
            topic = str(r[col_topic]).strip() if col_topic != -1 and len(r) > col_topic and r[col_topic] is not None else "Khác"
            diff = str(r[col_diff]).strip() if col_diff != -1 and len(r) > col_diff and r[col_diff] is not None else "Nhận biết"
            
            num = int(float(str(r[col_num]).strip())) if col_num != -1 and len(r) > col_num and str(r[col_num]).strip().replace('.','',1).isdigit() else idx

            options = {}
            if opt_a: options["A"] = opt_a
            if opt_b: options["B"] = opt_b
            if opt_c: options["C"] = opt_c
            if opt_d: options["D"] = opt_d

            questions.append({
                "question_number": num,
                "content": content,
                "options": options if options else None,
                "correct_answer": ans.upper(),
                "topic": topic,
                "difficulty_level": diff,
                "question_type": "trac_nghiem" if options else "tu_luan"
            })

        return {
            "type": "question_list",
            "data": questions
        }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python excel_parser.py <file_path>"}))
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(json.dumps({"error": f"File {file_path} not found"}))
        sys.exit(1)

    try:
        res = parse_excel(file_path)
        print(json.dumps(res, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
