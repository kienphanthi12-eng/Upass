import sys, json, io, os, re
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
    # Remove accents, spaces, special chars for simple matching
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn")
    return re.sub(r'[^a-zA-Z0-9]', '', s.lower())

def find_folder(title):
    target = clean_name(title)
    # Also clean the exam keywords
    # e.g., "De khao sat tot nghiep THPT 2026..."
    for folder in MINERU_DIR.iterdir():
        if folder.is_dir() and (folder / "full.md").exists():
            folder_clean = clean_name(folder.name)
            # Check if there is overlap or sub-string match
            if target in folder_clean or folder_clean in target:
                return folder
            # Fallback: check if first 20 characters of cleaned titles match
            if target[:30] in folder_clean or folder_clean[:30] in target:
                return folder
    return None

def main():
    exam_id = 81
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, display_title FROM exams WHERE id=%s", (exam_id,))
            exam = cur.fetchone()
            
    if not exam:
        print(f"Exam ID {exam_id} not found in DB.")
        return
        
    eid, title, display = exam
    print(f"Testing for Exam: {display} ({title})")
    
    folder = find_folder(title)
    if not folder:
        print(f"Could not find MinerU folder for: {title}")
        # Try a relaxed search
        folders = list(MINERU_DIR.glob("*Hải Phòng*"))
        if folders:
            folder = folders[0]
            print(f"Relaxed search found: {folder.name}")
        else:
            return
            
    md_path = folder / "full.md"
    text = md_path.read_text(encoding="utf-8")
    
    # Read the tail of the file (last 25000 characters)
    tail_text = text[-25000:]
    
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

    print("Sending tail text to DeepSeek...")
    resp = client.chat.completions.create(
        model="deepseek-chat",
        temperature=0,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Văn bản nguồn đề thi:\n\n{tail_text}"}
        ]
    )
    
    result = resp.choices[0].message.content.strip()
    print("--- Response ---")
    print(result)
    
    # Try parsing
    try:
        data = json.loads(result)
        print("Success! JSON parsed correctly.")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error parsing JSON: {e}")

if __name__ == "__main__":
    main()
