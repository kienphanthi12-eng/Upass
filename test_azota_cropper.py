"""
test_azota_cropper.py — Demo cắt câu hỏi từ PDF theo tọa độ (Giống công thức Azota PDF 2.0).

Cách hoạt động:
  1. Dùng PyMuPDF (fitz) phân tích cấu trúc khối văn bản (blocks) để lấy tọa độ y0 của các câu hỏi.
  2. Xác định phạm vi của từng câu hỏi trên trang.
  3. Hỗ trợ câu hỏi tràn trang: Nếu câu N nằm cuối trang 1 và kéo dài sang đầu trang 2, 
     script sẽ cắt phần cuối trang 1 và phần đầu trang 2, sau đó dùng Pillow ghép dọc 
     thành 1 ảnh duy nhất cho câu N.
  4. Render chất lượng cao (3x zoom = ~216 DPI) giữ nguyên bảng biểu, đồ thị vector.

Cách chạy:
  python test_azota_cropper.py [đường_dẫn_pdf]
"""

import os
import sys
import re
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Sửa lỗi hiển thị tiếng Việt trên Terminal Windows (tránh lỗi UnicodeEncodeError)
if sys.platform == "win32" and hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8" and not getattr(sys.stdout, "_custom_utf8", False):
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._custom_utf8 = True
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console()

# Thư mục chứa kết quả
OUTPUT_DIR = Path("output_crops")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Regex nhận diện đầu câu hỏi tiếng Việt & tiếng Anh phổ biến
QUESTION_PATTERN = re.compile(
    r"^\s*(Câu|Cau|Question|Quest|Bài|Bai|Part)\s*(\d+)\b", 
    re.IGNORECASE
)

# Regex nhận diện tiêu đề Phần (PHẦN I, PHẦN II, PHẦN III, Phần 1, Part I...)
SECTION_PATTERN = re.compile(
    r"^\s*(PHẦN|PHAN|PART|Phần|Phan|Part)\s*(I{1,3}|[123]|[A-Za-z]+)\b", 
    re.IGNORECASE
)

def clean_filename(title: str) -> str:
    """Lọc ký tự đặc biệt để làm tên thư mục."""
    return re.sub(r'[\\/*?:"<>| ]', '_', title)[:50]

def detect_questions_on_page(page, page_num: int) -> list[dict]:
    """
    Quét tất cả các block chữ trên trang để tìm đầu câu hỏi và tiêu đề Phần.
    Trả về list các elements được sắp xếp từ trên xuống dưới.
    """
    blocks = page.get_text("blocks")
    elements = []
    
    for b in blocks:
        x0, y0, x1, y1, text, block_no, block_type = b
        if block_type != 0:
            continue
            
        text_line = text.strip()
        
        # 1. Kiểm tra tiêu đề Phần trước
        sec_match = SECTION_PATTERN.match(text_line)
        if sec_match:
            elements.append({
                "type": "section",
                "sec_val": sec_match.group(2).upper(),
                "y0": y0,
                "text_preview": text_line.split('\n')[0][:60]
            })
            continue
            
        # 2. Kiểm tra đầu câu hỏi
        q_match = QUESTION_PATTERN.match(text_line)
        if q_match:
            elements.append({
                "type": "question",
                "q_num": int(q_match.group(2)),
                "y0": y0,
                "text_preview": text_line.split('\n')[0][:60]
            })
            
    # Sắp xếp theo thứ tự tọa độ từ trên xuống dưới
    elements.sort(key=lambda x: x["y0"])
    return elements

def crop_pdf_segment(page, y_start: float, y_end: float, zoom: float = 3.0) -> Image.Image:
    """
    Cắt một lát cắt ngang của trang PDF từ y_start đến y_end.
    Trả về một đối tượng PIL Image.
    """
    y_start = max(0.0, y_start)
    y_end = min(page.rect.y1, y_end)
    
    # Đảm bảo chiều cao hợp lệ (> 0)
    if y_end <= y_start:
        y_end = y_start + 1
        
    crop_rect = fitz.Rect(0, y_start, page.rect.x1, y_end)
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(clip=crop_rect, matrix=matrix)
    
    img_data = pix.samples
    img = Image.frombytes("RGB", [pix.width, pix.height], img_data)
    return img

def merge_images_vertically(images: list[Image.Image]) -> Image.Image:
    """Ghép dọc danh sách các ảnh lại với nhau."""
    if not images:
        raise ValueError("Danh sách ảnh trống")
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

def process_pdf(pdf_path: Path):
    if not pdf_path.exists():
        console.print(f"[bold red]Lỗi:[/] File không tồn tại tại '{pdf_path}'")
        return
        
    console.print(Panel(f"[bold green]Bắt đầu phân tích & cắt câu hỏi[/]\nFile: {pdf_path.name}", style="cyan"))
    
    pdf_output_dir = OUTPUT_DIR / clean_filename(pdf_path.stem)
    pdf_output_dir.mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    # Danh sách lưu mảnh ghép: { q_id: [ (page_num, PIL.Image), ... ] }
    question_slices: dict[str, list[tuple[int, Image.Image]]] = {}
    
    # ── Bước 1: Quét tọa độ tất cả các trang ─────────────────────────────────
    all_page_elements: dict[int, list[dict]] = {}
    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        all_page_elements[page_num] = detect_questions_on_page(page, page_num)
        
    # ── Bước 2: Cắt lát từng trang sử dụng State Machine ─────────────────────
    active_question = None  # Theo dõi câu hỏi đang bị cắt dở dang (ví dụ "Phần_I_Câu_12")
    current_section = "I"   # Theo dõi Phần hiện tại
    
    # Map chuyển số La Mã sang dạng hiển thị đẹp
    section_display = {
        "I": "I", "II": "II", "III": "III", "IV": "IV",
        "1": "I", "2": "II", "3": "III", "4": "IV"
    }
    
    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        elements = all_page_elements[page_num]
        page_height = page.rect.y1
        
        # Đếm số câu hỏi thực tế trên trang
        num_questions = sum(1 for el in elements if el["type"] == "question")
        console.print(f"Đang xử lý [bold yellow]Trang {page_num + 1}/{total_pages}[/] — Tìm thấy {num_questions} đầu câu hỏi.")
        
        # TH 1: Đầu trang có chứa phần tiếp nối của câu hỏi trước
        if active_question is not None:
            y_end_continuation = elements[0]["y0"] - 8 if elements else (page_height - 35)
            
            if y_end_continuation > 15:
                slice_img = crop_pdf_segment(page, 0, y_end_continuation)
                question_slices.setdefault(active_question, []).append((page_num, slice_img))
            
            if elements:
                # Đã gặp phần mới hoặc câu mới trên trang này → ngắt tràn trang cũ
                active_question = None
                
        # TH 2: Cắt các câu hỏi bắt đầu từ trang này
        for idx, el in enumerate(elements):
            if el["type"] == "section":
                current_section = section_display.get(el["sec_val"], el["sec_val"])
                active_question = None
                continue
                
            q_num = el["q_num"]
            q_id = f"Phần_{current_section}_Câu_{q_num}"
            y_start = el["y0"] - 8
            
            if idx + 1 < len(elements):
                y_end = elements[idx+1]["y0"] - 8
                active_question = None  # Không tràn trang vì có ranh giới kế tiếp
            else:
                y_end = page_height - 35
                active_question = q_id  # Bị tràn sang trang sau
                
            slice_img = crop_pdf_segment(page, y_start, y_end)
            question_slices.setdefault(q_id, []).append((page_num, slice_img))
            
    # ── Bước 3: Ghép dọc các mảnh của cùng 1 câu và lưu ảnh ──────────────────
    table = Table(title="Danh sách các câu hỏi đã cắt thành công")
    table.add_column("Tên câu", style="cyan", justify="left")
    table.add_column("Số mảnh ghép", style="magenta", justify="center")
    table.add_column("Các trang xuất hiện", style="green")
    table.add_column("File ảnh đầu ra", style="yellow")
    
    # Hàm sắp xếp khóa: Phan_I_Cau_1 -> (1, 1), Phan_II_Cau_4 -> (2, 4)
    def sort_key(q_key: str):
        parts = q_key.split("_")
        sec = parts[1]
        num = int(parts[3])
        sec_num = {"I": 1, "II": 2, "III": 3, "IV": 4}.get(sec, 99)
        return (sec_num, num)
        
    for q_id in sorted(question_slices.keys(), key=sort_key):
        slices_info = question_slices[q_id]
        pages_involved = sorted(list(set(p + 1 for p, _ in slices_info)))
        pages_str = ", ".join(str(p) for p in pages_involved)
        
        images = [img for _, img in slices_info]
        final_img = merge_images_vertically(images)
        
        # Định dạng tên file: Cau_I_01.png, Cau_II_02.png...
        parts = q_id.split("_")
        sec_str = parts[1]
        num_val = int(parts[3])
        filename = f"Cau_{sec_str}_{num_val:02d}.png"
        
        dest_path = pdf_output_dir / filename
        final_img.save(dest_path)
        
        # Tên câu hiển thị đẹp: Phần I - Câu 1
        display_name = f"Phần {sec_str} - Câu {num_val}"
        
        table.add_row(
            display_name,
            str(len(images)),
            f"Trang {pages_str}",
            dest_path.name
        )
        
    doc.close()
    
    console.print("\n")
    console.print(table)
    console.print(f"\n[bold green]✓ Đã hoàn thành![/] Tất cả ảnh câu hỏi được lưu tại: [bold yellow]{pdf_output_dir}[/]\n")

if __name__ == "__main__":
    # Chọn file PDF để chạy test
    pdf_to_test = Path("data/pdfs/test_vatly_lamdong.pdf")
    
    if len(sys.argv) > 1:
        pdf_to_test = Path(sys.argv[1])
        
    if not pdf_to_test.exists():
        # Fallback tìm kiếm file PDF bất kỳ trong data/pdfs
        pdf_dir = Path("data/pdfs")
        if pdf_dir.exists():
            pdfs = list(pdf_dir.glob("*.pdf"))
            if pdfs:
                pdf_to_test = pdfs[0]
                
    if not pdf_to_test.exists():
        console.print("[bold red]Lỗi:[/] Không tìm thấy file PDF nào để test. Hãy copy 1 file PDF vào thư mục data/pdfs/ hoặc truyền đường dẫn file vào lệnh.")
        sys.exit(1)
        
    process_pdf(pdf_to_test)
