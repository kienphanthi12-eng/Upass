"""scraper/scrape_dgnl.py — Scrape và tải đề thi Đánh giá năng lực / Đánh giá tư duy mới nhất.

Chạy:
    python scraper/scrape_dgnl.py
"""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import os
import json
import time
from pathlib import Path
import requests
from fake_useragent import UserAgent
from rich.console import Console

console = Console()
_ua = UserAgent()

# ── Config ────────────────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent.parent / "data" / "dgnl"
METADATA_FILE = Path(__file__).parent.parent / "data" / "dgnl_metadata.json"
TIMEOUT = 30
RATE = 1.5

# Danh sách các đề thi cần scrape
EXAMS_TO_SCRAPE = [
    {
        "id": "hsa_2025_toan",
        "title": "Đề tham khảo đánh giá năng lực môn Toán năm 2025 - Đại học Quốc gia Hà Nội (HSA)",
        "exam_type": "HSA",
        "year": "2025",
        "subject": "Toán học và Xử lý số liệu",
        "source_urls": [
            "https://toanmath.com/toanmath-pdf/de-tham-khao-danh-gia-nang-luc-mon-toan-nam-2025-dai-hoc-quoc-gia-ha-noi.pdf"
        ],
        "filename": "HSA_2025_De_Tham_Khao_Toan.pdf"
    },
    {
        "id": "apt_2025_tonghop",
        "title": "Đề thi minh họa và giới thiệu kỳ thi Đánh giá năng lực năm 2025 - Đại học Quốc gia TP.HCM (APT/V-ACT)",
        "exam_type": "APT",
        "year": "2025",
        "subject": "Tổng hợp (Ngôn ngữ, Toán học, Tư duy khoa học)",
        "source_urls": [
            "https://filethpt.hcm.shieldix.app/data/doc/2025/thptnguyenhien/tosinhnguyenhien/2025_3/25/2-de-minh-hoa-gioi-thieu-2025-final-0311-241112070045_253202520.pdf",
            "https://admintruong.haiphong.shieldix.app/data/doc/haiphong/2024/thptvinhbao/2024_11/18/de-minh-hoa-gioi-thieu-2025-final-03-11-241112070045-pdf_1811202417.pdf"
        ],
        "filename": "APT_2025_De_Minh_Hoa_Tong_Hop.pdf"
    },
    {
        "id": "tsa_2026_tonghop",
        "title": "Tuyển tập 10 đề thi thử kỳ thi Đánh giá tư duy năm 2026 - Đại học Bách khoa Hà Nội (TSA)",
        "exam_type": "TSA",
        "year": "2026",
        "subject": "Tổng hợp (Tư duy Toán, Đọc hiểu, Tư duy Khoa học)",
        "source_urls": [
            "https://toanmath.com/toanmath-pdf/tuyen-tap-10-de-thi-thu-ky-thi-danh-gia-tu-duy-dai-hoc-bach-khoa-ha-noi-tsa.pdf"
        ],
        "filename": "TSA_2026_Tuyen_Tap_10_De_Thi_Thu.pdf"
    },
    {
        "id": "hnue_2025_toan",
        "title": "Đề tham khảo đánh giá năng lực môn Toán năm 2025 - Trường Đại học Sư phạm Hà Nội (HNUE)",
        "exam_type": "HNUE",
        "year": "2025",
        "subject": "Toán học",
        "source_urls": [
            "https://toanmath.com/toanmath-pdf/de-tham-khao-dgnl-mon-toan-xet-tuyen-dai-hoc-2025-truong-dhsp-ha-noi.pdf"
        ],
        "filename": "HNUE_2025_De_Tham_Khao_Toan.pdf"
    },
    {
        "id": "hcmue_2025_toan",
        "title": "Đề minh họa đánh giá năng lực chuyên biệt môn Toán năm 2025 - Trường Đại học Sư phạm TP.HCM (HCMUE)",
        "exam_type": "HCMUE",
        "year": "2025",
        "subject": "Toán học chuyên biệt",
        "source_urls": [
            "https://toanmath.com/toanmath-pdf/de-minh-hoa-danh-gia-nang-luc-mon-toan-nam-2025-truong-dhsp-tp-ho-chi-minh.pdf"
        ],
        "filename": "HCMUE_2025_De_Minh_Hoa_Toan.pdf"
    }
]

def download_file(url, dest_path):
    headers = {
        "User-Agent": _ua.random,
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
        
        # Đọc chunk đầu tiên để check định dạng PDF
        chunk = next(r.iter_content(64), b"")
        if not chunk.startswith(b"%PDF") and not url.lower().endswith(".pdf"):
            console.print(f"[yellow]  Cảnh báo: File tải về có thể không phải PDF hợp lệ (URL: {url})[/yellow]")
        
        buf = io.BytesIO()
        buf.write(chunk)
        for c in r.iter_content(8192):
            buf.write(c)
            
        dest_path.write_bytes(buf.getvalue())
        size_kb = dest_path.stat().st_size // 1024
        console.print(f"[green]  Tải thành công: {dest_path.name} ({size_kb} KB)[/green]")
        return True
    except Exception as e:
        console.print(f"[red]  Lỗi khi tải {url}: {e}[/red]")
        return False

def run():
    console.print("[bold cyan]=== BẮT ĐẦU SCRAPE ĐỀ THI ĐÁNH GIÁ NĂNG LỰC / TƯ DUY ===[/bold cyan]")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    metadata = []
    success_count = 0
    
    for item in EXAMS_TO_SCRAPE:
        console.print(f"\n[bold]Đang tải: {item['title']}[/bold]")
        dest = OUT_DIR / item["filename"]
        
        # Kiểm tra file đã có sẵn và có hợp lệ không
        is_valid_pdf = False
        if dest.exists():
            try:
                with open(dest, "rb") as fh:
                    is_valid_pdf = fh.read(4).startswith(b"%PDF")
            except Exception:
                pass
        
        if dest.exists() and is_valid_pdf:
            console.print(f"[dim]  File đã tồn tại và hợp lệ: {item['filename']} (Bỏ qua download)[/dim]")
            ok = True
            scraped_url = item["source_urls"][0]
        else:
            if dest.exists():
                console.print(f"[yellow]  File đã tồn tại nhưng không hợp lệ (bị lỗi header). Tiến hành tải lại...[/yellow]")
            ok = False
            scraped_url = ""
            for url in item["source_urls"]:
                ok = download_file(url, dest)
                if ok:
                    scraped_url = url
                    break
                time.sleep(RATE)
            
        if ok:
            success_count += 1
            # Thêm thông tin vào metadata
            # Lưu đường dẫn tương đối từ thư mục gốc dự án để dễ import sau này
            rel_path = f"data/dgnl/{item['filename']}"
            metadata.append({
                "id": item["id"],
                "title": item["title"],
                "exam_type": item["exam_type"],
                "year": item["year"],
                "subject": item["subject"],
                "file_path": rel_path,
                "absolute_path": str(dest.resolve()),
                "source_url": scraped_url,
                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "file_size_bytes": dest.stat().st_size if dest.exists() else 0
            })
            
    # Lưu metadata vào file JSON riêng biệt
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        console.print(f"\n[bold green]✓ Đã lưu metadata của tất cả đề thi vào file: {METADATA_FILE.name}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Lỗi khi lưu file metadata: {e}[/bold red]")
        
    console.print(f"\n[bold cyan]=== HOÀN THÀNH: Tải thành công {success_count}/{len(EXAMS_TO_SCRAPE)} đề ĐGNL ===[/bold cyan]")

if __name__ == "__main__":
    run()
