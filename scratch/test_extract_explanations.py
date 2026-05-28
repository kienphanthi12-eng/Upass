import re
import sys
import io
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Fix console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, '.')
import config
from openai import AsyncOpenAI

deepseek = AsyncOpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

MINERU_DIR = Path("C:/Users/HP/MinerU")
folder = "thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Vat-Li-So-GD-Lam-Dong-.pdf-406acd9e-0fbe-4aa4-adc3-af839963a842"

KEYWORDS = [
    r"(?i)(?:##?\s*)?LỜI\s*GIẢI\s*THAM\s*KHẢO",
    r"(?i)(?:##?\s*)?LOI\s*GIAI\s*THAM\s*KHAO",
    r"(?i)(?:##?\s*)?LỜI\s*GIẢI\s*CHI\s*TIẾT",
    r"(?i)(?:##?\s*)?LOI\s*GIAI\s*CHI\s*TIET",
    r"(?i)(?:##?\s*)?HƯỚNG\s*DẪN\s*GIẢI\s*CHI\s*TIẾT",
    r"(?i)(?:##?\s*)?HUONG\s*DAN\s*GIAI\s*CHI\s*TIET",
    r"(?i)(?:##?\s*)?HƯỚNG\s*DẪN\s*GIẢI",
    r"(?i)(?:##?\s*)?HUONG\s*DAN\s*GIAI",
    r"(?i)(?:##?\s*)?ĐÁP\s*ÁN\s*CHI\s*TIẾT",
    r"(?i)(?:##?\s*)?DAP\s*AN\s*CHI\s*TIET",
    r"(?i)(?:##?\s*)?BẢNG\s*ĐÁP\s*ÁN",
    r"(?i)(?:##?\s*)?BANG\s*DAP\s*AN",
    r"(?i)(?:##?\s*)?ĐÁP\s*ÁN\s*-\s*LỜI\s*GIẢI",
    r"(?i)(?:##?\s*)?DAP\s*AN\s*-\s*LOI\s*GIAI",
    r"(?i)LOI\s*GIAI\s*THAM\s*KHAO",
    r"(?i)LỜI\s*GIẢI\s*THAM\s*KHẢO",
    r"(?i)PHẦN\s*I\s*[-–]\s*ĐÁP\s*ÁN",
    r"(?i)PHAN\s*I\s*[-–]\s*DAP\s*AN"
]

def split_raw_markdown(text: str):
    best_idx = -1
    for kw in KEYWORDS:
        matches = list(re.finditer(kw, text))
        if matches:
            idx = matches[0].start()
            if best_idx == -1 or idx < best_idx:
                best_idx = idx
    if best_idx == -1:
        for m in re.finditer(r"(?i)(?:##?\s*)?Phan\s*I", text):
            sub = text[m.start():m.start()+500]
            if "table" in sub or "|" in sub:
                best_idx = m.start()
                break
    if best_idx != -1:
        return text[:best_idx], text[best_idx:]
    return text, ""

async def main():
    p = MINERU_DIR / folder / "full.md"
    if not p.exists():
        print("Folder not found")
        return
    
    text = p.read_text(encoding="utf-8")
    q_part, a_part = split_raw_markdown(text)
    
    print(f"Explanations section size: {len(a_part)} characters")
    
    system_prompt = """\
Bạn là chuyên gia trích xuất đáp án và lời giải từ phần hướng dẫn giải của đề thi THPT Việt Nam (Toán, Lý, Hóa, Sử, Anh).
Nhiệm vụ: Nhận đoạn văn bản hướng dẫn giải chi tiết và trích xuất đáp án cùng lời giải chi tiết cho từng câu hỏi.

Trả về duy nhất 1 đối tượng JSON có định dạng sau:
{
  "part_1": {
    "1": {
      "answer": "A", // Đáp án của Câu 1 phần I (A, B, C hoặc D)
      "explanation": "Lời giải chi tiết của Câu 1..." // Lời giải chi tiết (giữ nguyên LaTeX và ảnh nếu có)
    },
    ...
  },
  "part_2": {
    "1": {
      "answer": "DSDD", // Đáp án của Câu 1 phần II (gồm 4 chữ cái D hoặc S tương ứng với a, b, c, d)
      "explanation": "Lời giải chi tiết cho các ý a, b, c, d..."
    },
    ...
  },
  "part_3": {
    "1": {
      "answer": "1067", // Đáp án ngắn của Câu 1 phần III (số hoặc cụm từ ngắn)
      "explanation": "Lời giải chi tiết..."
    },
    ...
  }
}

Lưu ý:
1. Nếu đề thi không chia phần (ví dụ đề Tiếng Anh chỉ có trắc nghiệm), hãy trích xuất toàn bộ vào "part_1".
2. Giữ nguyên định dạng LaTeX ($...$, $$...$$) và ảnh (![...](...)) trong lời giải chi tiết.
3. Không tự chế câu hỏi, chỉ trích xuất từ văn bản hướng dẫn giải được cung cấp.
"""
    print("Calling DeepSeek-V3...")
    resp = await deepseek.chat.completions.create(
        model="deepseek-chat",
        temperature=0,
        max_tokens=4096,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Trích xuất đáp án và lời giải từ văn bản sau:\n\n{a_part}"},
        ],
    )
    result = resp.choices[0].message.content
    
    # Save the output
    Path("data/test_extracted_explanations.json").write_text(result, encoding="utf-8")
    print("Successfully saved to data/test_extracted_explanations.json")

if __name__ == "__main__":
    asyncio.run(main())
