"""
processor/crop_pdf_job.py — Job chạy ngầm cắt câu hỏi PDF thành ảnh (PDF 2.0).

Chạy bởi: Node.js (spawn) sau khi giáo viên upload file PDF với kiểu import là 'pdf2'.
Quy trình:
  1. Parse arguments: pdf_path, job_id, user_id, filename.
  2. Quét tọa độ, render và crop câu hỏi thành ảnh chất lượng cao.
  3. Upload ảnh câu hỏi lên Supabase Storage (bucket: 'exam-images').
  4. Tạo bản ghi 'draft_exams' & các câu hỏi trong 'draft_questions' chứa link ảnh.
  5. Cập nhật trạng thái 'ocr_jobs' → 'done'.
"""

import os
import sys
import re
import argparse
import requests
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF

# Thiết lập sys.path để import db và config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import db
import config

# Sửa lỗi hiển thị tiếng Việt trên Terminal Windows (tránh lỗi UnicodeEncodeError)
if sys.platform == "win32" and hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8" and not getattr(sys.stdout, "_custom_utf8", False):
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._custom_utf8 = True
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load web/.env.local specifically for Supabase keys
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', '.env.local'))

# Cấu hình Supabase từ .env
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", f"https://{os.getenv('SUPABASE_PROJECT_ID', 'zabvdgnucfanvbjjgnic')}.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")

# BUCKET lưu trữ ảnh
BUCKET_NAME = "exam-images"

# Patterns nhận diện cấu trúc đề
QUESTION_PATTERN = re.compile(
    r"^\s*(Câu|Cau|Question|Quest|Bài|Bai|Part)\s*(\d+)\b", 
    re.IGNORECASE
)
SECTION_PATTERN = re.compile(
    r"^\s*(PHẦN|PHAN|PART|Phần|Phan|Part)\s*(I{1,3}|[123]|[A-Za-z]+)\b", 
    re.IGNORECASE
)
SECTION_MAP = {
    "I": 1, "II": 2, "III": 3, "IV": 4,
    "1": 1, "2": 2, "3": 3, "4": 4
}
SECTION_QTYPE = {
    1: "trac_nghiem",
    2: "dung_sai",
    3: "tu_luan"
}

def detect_elements_on_page(page) -> list[dict]:
    """Tìm đầu câu và tiêu đề phần trên trang."""
    blocks = page.get_text("blocks")
    elements = []
    
    for b in blocks:
        x0, y0, x1, y1, text, block_no, block_type = b
        if block_type != 0:
            continue
            
        text_line = text.strip()
        
        # 1. Tìm tiêu đề Phần
        sec_match = SECTION_PATTERN.match(text_line)
        if sec_match:
            elements.append({
                "type": "section",
                "sec_val": sec_match.group(2).upper(),
                "y0": y0
            })
            continue
            
        # 2. Tìm câu hỏi
        q_match = QUESTION_PATTERN.match(text_line)
        if q_match:
            elements.append({
                "type": "question",
                "q_num": int(q_match.group(2)),
                "y0": y0
            })
            
    elements.sort(key=lambda x: x["y0"])
    return elements

import json

def find_options_in_range(words, y_start, y_end):
    """Tìm tọa độ A, B, C, D (hoặc a, b, c, d) làm đầu đáp án trong khoảng y."""
    candidates = []
    for w in words:
        x0, y0, x1, y1, word, block_no, line_no, word_no = w
        if y_start <= y0 <= y_end:
            candidates.append({
                "word": word,
                "bbox": (x0, y0, x1, y1)
            })
            
    markers = {}
    for letter in ['A', 'B', 'C', 'D']:
        # Strip trailing dots or parenthesis to support 'A.', 'A)', 'a.', 'a)'
        occs = [c for c in candidates if c["word"].strip(".)").upper() == letter]
        if not occs:
            return None
        markers[letter] = occs
        
    best_match = None
    for a in markers['A']:
        for b in markers['B']:
            if b["bbox"][1] < a["bbox"][1] - 5: continue
            for c in markers['C']:
                if c["bbox"][1] < b["bbox"][1] - 5: continue
                for d in markers['D']:
                    if d["bbox"][1] < c["bbox"][1] - 5: continue
                    best_match = {'A': a, 'B': b, 'C': c, 'D': d}
                    break
                if best_match: break
            if best_match: break
        if best_match: break
        
    return best_match

def crop_pdf_segment(page, y_start: float, y_end: float, x_start: float = 0.0, x_end: float = None, zoom: float = 3.0) -> Image.Image:
    """Cắt lát cắt dọc/ngang trang PDF và trả về đối tượng PIL Image."""
    if x_end is None:
        x_end = page.rect.x1
    y_start = max(0.0, y_start)
    y_end = min(page.rect.y1, y_end)
    x_start = max(0.0, x_start)
    x_end = min(page.rect.x1, x_end)
    if y_end <= y_start:
        y_end = y_start + 1
    if x_end <= x_start:
        x_end = x_start + 1
        
    crop_rect = fitz.Rect(x_start, y_start, x_end, y_end)
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(clip=crop_rect, matrix=matrix)
    
    img_data = pix.samples
    img = Image.frombytes("RGB", [pix.width, pix.height], img_data)
    return img

def merge_images_vertically(images: list[Image.Image]) -> Image.Image:
    """Ghép dọc các ảnh lại với nhau."""
    if len(images) == 1:
        return images[0]
    width = max(img.width for img in images)
    total_height = sum(img.height for img in images)
    merged_image = Image.new("RGB", (width, total_height), (255, 255, 255))
    current_y = 0
    for img in images:
        merged_image.paste(img, (0, current_y))
        current_y += img.height
    return merged_image

def upload_image_to_supabase_or_local(file_path: Path, storage_path: str, user_id: str, job_id: str, temp_filename: str) -> str:
    """Upload ảnh lên Supabase Storage và trả về public URL. Nếu lỗi/không có key, tự động lưu local và trả về relative URL."""
    if SUPABASE_SERVICE_KEY and SUPABASE_SERVICE_KEY != "your_service_role_key_here":
        try:
            upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{storage_path}"
            headers = {
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "image/png"
            }
            with open(file_path, "rb") as f:
                data = f.read()
                
            # Thử POST trước (cho file mới)
            resp = requests.post(upload_url, data=data, headers=headers)
            if resp.status_code not in (200, 201):
                # Thử PUT nếu đã tồn tại (để ghi đè)
                resp = requests.put(upload_url, data=data, headers=headers)
                
            if resp.status_code in (200, 201):
                return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{storage_path}"
            else:
                print(f"Supabase storage upload failed with status {resp.status_code}, trying local fallback")
        except Exception as e:
            print(f"Supabase storage upload exception: {e}, trying local fallback")
            
    # Fallback: copy file vào Next.js public directory
    try:
        root_dir = Path(__file__).parent.parent
        local_dir = root_dir / "web" / "public" / "exam-images" / user_id / job_id
        local_dir.mkdir(parents=True, exist_ok=True)
        local_file_path = local_dir / temp_filename
        shutil.copy2(file_path, local_file_path)
        return f"/exam-images/{user_id}/{job_id}/{temp_filename}"
    except Exception as local_err:
        print(f"Local storage fallback failed: {local_err}")
        return f"/exam-images/{user_id}/{job_id}/{temp_filename}"

def main():
    parser = argparse.ArgumentParser(description="Background PDF question cropper.")
    parser.add_argument("--pdf_path", required=True, help="Path to input PDF file")
    parser.add_argument("--job_id", required=True, help="UUID of the ocr_job")
    parser.add_argument("--user_id", required=True, help="UUID of the teacher user")
    parser.add_argument("--filename", required=True, help="Original uploaded filename")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    job_id = args.job_id
    user_id = args.user_id
    original_filename = args.filename
    
    if not pdf_path.exists():
        print(f"File {pdf_path} not found")
        sys.exit(1)
        
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Mở PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        all_page_elements = {}
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            all_page_elements[page_num] = detect_elements_on_page(page)
            
        question_ranges = []
        active_range = None
        current_section = "I"
        
        # ── Bước 1: Thu thập tọa độ câu hỏi và xử lý tràn trang ───────────────
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            elements = all_page_elements[page_num]
            page_height = page.rect.y1
            
            # TH 1: Đầu trang có phần tiếp nối của câu hỏi trước
            if active_range is not None:
                y_end_continuation = elements[0]["y0"] - 8 if elements else (page_height - 35)
                if y_end_continuation > 15:
                    active_range["spans"].append((page_num, 0.0, y_end_continuation))
                if elements:
                    active_range = None
                    
            # TH 2: Các câu hỏi bắt đầu từ trang này
            for idx, el in enumerate(elements):
                if el["type"] == "section":
                    current_section = el["sec_val"]
                    active_range = None
                    continue
                    
                q_num = el["q_num"]
                sec_num = SECTION_MAP.get(current_section, 1)
                q_id = f"Phần_{current_section}_Câu_{q_num}"
                y_start = el["y0"] - 8
                
                if idx + 1 < len(elements):
                    y_end = elements[idx+1]["y0"] - 8
                    active_range = None
                else:
                    y_end = page_height - 35
                    
                q_range = {
                    "q_id": q_id,
                    "sec_str": current_section,
                    "sec_num": sec_num,
                    "num_val": q_num,
                    "spans": [(page_num, y_start, y_end)]
                }
                question_ranges.append(q_range)
                if idx + 1 == len(elements):
                    active_range = q_range
                    
        # ── Bước 2: Cắt ảnh chi tiết và phân chia Đề / Đáp án ─────────────────
        questions_to_insert = []
        
        for q_range in question_ranges:
            q_id = q_range["q_id"]
            sec_str = q_range["sec_str"]
            sec_num = q_range["sec_num"]
            num_val = q_range["num_val"]
            spans = q_range["spans"]
            
            q_type = SECTION_QTYPE.get(sec_num, "trac_nghiem")
            db_q_number = num_val + (sec_num - 1) * 100
            
            # Chỉ thử tách đáp án với phần Trắc nghiệm (Phần I) hoặc Đúng/Sai (Phần II)
            opts = None
            if q_type in ("trac_nghiem", "dung_sai"):
                # Đáp án thường ở trang/lát cuối cùng của câu hỏi
                opt_page_num, y_start_span, y_end_span = spans[-1]
                opt_words = doc.load_page(opt_page_num).get_text("words")
                opts = find_options_in_range(opt_words, y_start_span, y_end_span)
                
            if opts:
                # Tìm thấy 4 đáp án A, B, C, D
                box_A, box_B, box_C, box_D = opts['A']["bbox"], opts['B']["bbox"], opts['C']["bbox"], opts['D']["bbox"]
                y_A, y_B, y_C, y_D = box_A[1], box_B[1], box_C[1], box_D[1]
                
                y_opt_start = min(y_A, y_B, y_C, y_D) - 8
                opt_page_num, y_start_span, y_end_span = spans[-1]
                opt_page = doc.load_page(opt_page_num)
                
                # Cắt stem (đề): từ y_start_span đến y_opt_start của lát cuối
                stem_spans = spans[:-1] + [(opt_page_num, y_start_span, y_opt_start)]
                stem_images = []
                for p_num, ys, ye in stem_spans:
                    stem_images.append(crop_pdf_segment(doc.load_page(p_num), ys, ye))
                merged_stem = merge_images_vertically(stem_images)
                
                stem_filename = f"q_{sec_str}_{num_val:02d}_stem.png"
                stem_filepath = temp_dir / stem_filename
                merged_stem.save(stem_filepath, "PNG")
                stem_url = upload_image_to_supabase_or_local(stem_filepath, f"{user_id}/{job_id}/{stem_filename}", user_id, job_id, stem_filename)
                
                # Phân loại layout và cắt 4 đáp án
                is_horizontal = abs(y_A - y_B) < 10 and abs(y_B - y_C) < 10 and abs(y_C - y_D) < 10
                is_2x2 = abs(y_A - y_B) < 10 and abs(y_C - y_D) < 10 and abs(y_A - y_C) >= 10
                
                opt_imgs = {}
                
                if is_horizontal:
                    # Layout ngang (1 dòng)
                    x_A, x_B, x_C, x_D = box_A[0], box_B[0], box_C[0], box_D[0]
                    m_AB = x_B - 8
                    m_BC = x_C - 8
                    m_CD = x_D - 8
                    
                    opt_imgs['A'] = crop_pdf_segment(opt_page, y_opt_start, y_end_span, 0, m_AB)
                    opt_imgs['B'] = crop_pdf_segment(opt_page, y_opt_start, y_end_span, m_AB, m_BC)
                    opt_imgs['C'] = crop_pdf_segment(opt_page, y_opt_start, y_end_span, m_BC, m_CD)
                    opt_imgs['D'] = crop_pdf_segment(opt_page, y_opt_start, y_end_span, m_CD, opt_page.rect.x1)
                    
                elif is_2x2:
                    # Layout 2x2
                    center_x = opt_page.rect.x1 / 2
                    y_row2 = min(y_C, y_D) - 8
                    
                    opt_imgs['A'] = crop_pdf_segment(opt_page, y_opt_start, y_row2, 0, center_x)
                    opt_imgs['B'] = crop_pdf_segment(opt_page, y_opt_start, y_row2, center_x, opt_page.rect.x1)
                    opt_imgs['C'] = crop_pdf_segment(opt_page, y_row2, y_end_span, 0, center_x)
                    opt_imgs['D'] = crop_pdf_segment(opt_page, y_row2, y_end_span, center_x, opt_page.rect.x1)
                    
                else:
                    # Layout dọc (4 dòng)
                    sorted_markers = sorted([opts['A'], opts['B'], opts['C'], opts['D']], key=lambda m: m["bbox"][1])
                    L1, L2, L3, L4 = [m["word"].strip(".)").upper() for m in sorted_markers]
                    
                    opt_imgs[L1] = crop_pdf_segment(opt_page, sorted_markers[0]["bbox"][1] - 8, sorted_markers[1]["bbox"][1] - 8)
                    opt_imgs[L2] = crop_pdf_segment(opt_page, sorted_markers[1]["bbox"][1] - 8, sorted_markers[2]["bbox"][1] - 8)
                    opt_imgs[L3] = crop_pdf_segment(opt_page, sorted_markers[2]["bbox"][1] - 8, sorted_markers[3]["bbox"][1] - 8)
                    opt_imgs[L4] = crop_pdf_segment(opt_page, sorted_markers[3]["bbox"][1] - 8, y_end_span)
                
                # Upload các ảnh đáp án
                options_dict = {}
                for letter in ['A', 'B', 'C', 'D']:
                    opt_img = opt_imgs.get(letter)
                    if opt_img:
                        opt_filename = f"q_{sec_str}_{num_val:02d}_opt_{letter}.png"
                        opt_filepath = temp_dir / opt_filename
                        opt_img.save(opt_filepath, "PNG")
                        opt_url = upload_image_to_supabase_or_local(opt_filepath, f"{user_id}/{job_id}/{opt_filename}", user_id, job_id, opt_filename)
                        options_dict[letter] = f"![{letter}]({opt_url})"
                    else:
                        options_dict[letter] = ""
                
                questions_to_insert.append({
                    "question_number": db_q_number,
                    "question_type": q_type,
                    "content": f"![Câu hỏi {sec_str} - {num_val}]({stem_url})",
                    "options": options_dict,
                    "difficulty_level": "Nhận biết"
                })
                
            else:
                # Không tìm thấy đáp án hoặc là tự luận -> Cắt nguyên khối
                images = []
                for p_num, ys, ye in spans:
                    images.append(crop_pdf_segment(doc.load_page(p_num), ys, ye))
                merged_img = merge_images_vertically(images)
                
                temp_filename = f"q_{sec_str}_{num_val:02d}.png"
                temp_file_path = temp_dir / temp_filename
                merged_img.save(temp_file_path, "PNG")
                public_url = upload_image_to_supabase_or_local(temp_file_path, f"{user_id}/{job_id}/{temp_filename}", user_id, job_id, temp_filename)
                
                questions_to_insert.append({
                    "question_number": db_q_number,
                    "question_type": q_type,
                    "content": f"![Câu hỏi {sec_str} - {num_val}]({public_url})",
                    "options": None,
                    "difficulty_level": "Nhận biết"
                })
                
        # ── Bước 3: Chèn vào Database bằng psycopg2 (qua database.db) ────────────────
        exam_title = re.sub(r'[-_]', ' ', original_filename.rsplit('.', 1)[0])
        
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                # 1. Tạo Draft Exam
                cur.execute(
                    """INSERT INTO draft_exams (teacher_id, ocr_job_id, title, status)
                       VALUES (%s, %s, %s, 'draft') RETURNING id""",
                    (user_id, job_id, exam_title)
                )
                draft_exam_id = cur.fetchone()[0]
                
                # 2. Chèn Draft Questions (bao gồm cột options)
                for q in questions_to_insert:
                    cur.execute(
                        """INSERT INTO draft_questions 
                           (draft_exam_id, question_number, question_type, content, options, difficulty_level)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (draft_exam_id, q["question_number"], q["question_type"], q["content"],
                         json.dumps(q["options"]) if q.get("options") else None, q["difficulty_level"])
                    )
                    
                # 3. Cập nhật trạng thái OCR Job
                cur.execute(
                    """UPDATE ocr_jobs 
                       SET status = 'done', question_count = %s, updated_at = NOW()
                       WHERE id = %s""",
                    (len(questions_to_insert), job_id)
                )
        
        print(f"Job {job_id} completed successfully. Created draft exam {draft_exam_id} with {len(questions_to_insert)} questions.")
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error executing job {job_id}: {error_msg}")
        
        # Cập nhật ocr_jobs trạng thái lỗi
        try:
            with db.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE ocr_jobs 
                           SET status = 'error', error_msg = %s, updated_at = NOW()
                           WHERE id = %s""",
                        (error_msg, job_id)
                    )
        except Exception as db_ex:
            print(f"Could not update error state in DB: {db_ex}")
            
    finally:
        # Xóa file tạm
        shutil.rmtree(temp_dir, ignore_errors=True)
        try:
            os.unlink(pdf_path)
        except:
            pass

if __name__ == "__main__":
    main()

