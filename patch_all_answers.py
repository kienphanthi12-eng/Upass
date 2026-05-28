import sys, json, io, os, re, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from openai import OpenAI
import config
from database import db; db.init_pool()

client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

MINERU_DIR = Path("C:/Users/HP/MinerU")

def clean_name(name):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn")
    return re.sub(r'[^a-zA-Z0-9]', '', s.lower())

def find_folder(title):
    target = clean_name(title)
    # Direct match
    for folder in MINERU_DIR.iterdir():
        if folder.is_dir() and (folder / "full.md").exists():
            folder_clean = clean_name(folder.name)
            if target in folder_clean or folder_clean in target:
                return folder
            if target[:35] in folder_clean or folder_clean[:35] in target:
                return folder
                
    # Relaxed search by keywords
    # Try splitting target into keywords and finding a folder containing most keywords
    keywords = [w for w in re.split(r'\d+', title) if len(w) > 3]
    if keywords:
        best_folder = None
        max_matches = 0
        for folder in MINERU_DIR.iterdir():
            if folder.is_dir() and (folder / "full.md").exists():
                matches = sum(1 for kw in keywords if clean_name(kw) in clean_name(folder.name))
                if matches > max_matches:
                    max_matches = matches
                    best_folder = folder
        if max_matches >= 2: # At least 2 keyword matches
            return best_folder

    return None

def extract_answers_from_text(tail_text, exam_title):
    prompt = """Bạn là một chuyên gia toán học và xử lý dữ liệu đề thi.
Dưới đây là phần cuối của một tệp Markdown chứa đề thi thử môn Toán THPT (bao gồm các bảng đáp án và hướng dẫn giải).
Nhiệm vụ của bạn là trích xuất bảng đáp án cho toàn bộ đề thi này và trả về dưới dạng JSON.

Quy tắc ánh xạ số câu hỏi lên hệ thống:
1. Phần I (Trắc nghiệm): gồm 12 câu (Câu 1 đến Câu 12). Đáp án đúng là các ký tự A, B, C hoặc D. Ánh xạ vào các khóa JSON: "1" đến "12".
2. Phần II (Đúng/Sai): gồm 4 câu (Câu 1 đến Câu 4). Mỗi câu có 4 ý phụ (a, b, c, d), đáp án mỗi ý phụ là Đúng (D) hoặc Sai (S). Bạn cần kết hợp đáp án 4 ý này thành một chuỗi 4 ký tự (ví dụ: DSDS, SSDD, DDSS,...). Ánh xạ vào các khóa JSON: "101" đến "104" (Câu 1 tương ứng "101", Câu 2 tương ứng "102",...).
3. Phần III (Tự luận ngắn/điền số): gồm 6 đến 7 câu (Câu 1 đến Câu 6 hoặc 7). Đáp án là các số nguyên hoặc số thập phân (ví dụ: 1.5, -4, 120,...). Ánh xạ vào các khóa JSON: "201" đến "207" (Câu 1 tương ứng "201", Câu 2 tương ứng "202",...).

Vui lòng trả về DUY NHẤT một đối tượng JSON có định dạng như sau:
{
  "1": "A",
  "2": "B",
  ...
  "101": "DSDS",
  "102": "SSDD",
  ...
  "201": "1.5",
  "202": "170"
}

Nếu câu hỏi nào không thể tìm thấy đáp án trong đoạn văn bản cung cấp, hãy bỏ qua hoặc trả về null cho khóa đó.
Chỉ trả về JSON thô, không thêm dấu nháy ngược markdown (```json), không giải thích gì thêm."""

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            temperature=0,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Văn bản nguồn đề thi '{exam_title}':\n\n{tail_text}"}
            ]
        )
        content = resp.choices[0].message.content.strip()
        # Find JSON block if DeepSeek added prefix/suffix
        m = re.search(r'\{[\s\S]+\}', content)
        if m:
            return json.loads(m.group(0))
        return json.loads(content)
    except Exception as e:
        print(f"Error calling/parsing DeepSeek: {e}")
        return None

def main():
    print("Starting batch answer patching process...")
    
    # 1. Get all exams with done status
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, display_title FROM exams WHERE ocr_status='done' ORDER BY id")
            exams = cur.fetchall()
            
    print(f"Found {len(exams)} exams in database.")
    
    success_count = 0
    fail_count = 0
    total_updated = 0
    
    for exam_id, title, display_title in exams:
        exam_name = display_title if display_title else title
        print(f"\nProcessing: {exam_name} (ID: {exam_id})")
        
        # Check if this exam is missing answers
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM questions 
                    WHERE exam_id = %s AND is_hidden = false AND correct_answer IS NULL
                """, (exam_id,))
                missing_ans_count = cur.fetchone()[0]
                
        if missing_ans_count == 0:
            print(f"  -> All questions in {exam_name} already have answers. Skipping.")
            continue
            
        print(f"  -> Has {missing_ans_count} questions missing answers. Locating file...")
        folder = find_folder(title)
        if not folder:
            print(f"  -> ERROR: Could not find MinerU folder for: {title}")
            fail_count += 1
            continue
            
        print(f"  -> Found folder: {folder.name}")
        md_path = folder / "full.md"
        if not md_path.exists():
            print(f"  -> ERROR: full.md does not exist in folder.")
            fail_count += 1
            continue
            
        # Read the tail of the file
        try:
            text = md_path.read_text(encoding="utf-8")
            tail_text = text[-30000:] # Last 30000 chars to ensure we capture all tables
        except Exception as e:
            print(f"  -> ERROR reading file: {e}")
            fail_count += 1
            continue
            
        print(f"  -> Sending to DeepSeek for answer key extraction...")
        answers = extract_answers_from_text(tail_text, title)
        if not answers:
            print(f"  -> ERROR: Failed to extract answers using DeepSeek.")
            fail_count += 1
            continue
            
        print(f"  -> Successfully extracted {len(answers)} answers from file.")
        
        # 2. Update database questions
        updated_questions = 0
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                for q_num_str, ans_val in answers.items():
                    if ans_val is None:
                        continue
                    try:
                        q_num = int(q_num_str)
                    except ValueError:
                        continue
                    
                    # Update correct_answer if it was NULL (or always update to ensure correctness)
                    cur.execute("""
                        UPDATE questions 
                        SET correct_answer = %s 
                        WHERE exam_id = %s AND question_number = %s
                        RETURNING id
                    """, (str(ans_val).strip(), exam_id, q_num))
                    updated = cur.fetchall()
                    if updated:
                        updated_questions += 1
                conn.commit()
                
        print(f"  -> Database updated: {updated_questions} questions set with correct answers.")
        total_updated += updated_questions
        success_count += 1
        
        # Small delay to respect rate limits if any
        time.sleep(1)
        
    print("\n========================================")
    print(f"Batch processing completed.")
    print(f"Successfully processed: {success_count} exams.")
    print(f"Failed to process: {fail_count} exams.")
    print(f"Total questions updated: {total_updated}.")
    print("========================================")

if __name__ == "__main__":
    main()
