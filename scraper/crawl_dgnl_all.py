"""scraper/crawl_dgnl_all.py — Tìm kiếm và tải hàng loạt đề thi ĐGNL / ĐGTD từ internet.

Chạy:
    python scraper/crawl_dgnl_all.py
"""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import os
import re
import json
import time
import unicodedata
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from rich.console import Console

console = Console()
_ua = UserAgent()

# ── Config ────────────────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent.parent / "data" / "dgnl"
METADATA_FILE = Path(__file__).parent.parent / "data" / "dgnl_metadata.json"
TIMEOUT = 30
RATE = 1.0  # Giãn cách 1 giây để tránh bị chặn

# Danh sách từ khóa tìm kiếm
SEARCH_QUERIES = [
    "đánh giá năng lực",
    "đánh giá tư duy",
    "dgnl",
    "tsa",
    "thi thử đánh giá năng lực",
    "thi thử đánh giá tư duy",
    "đề minh họa đánh giá năng lực",
    "đề minh họa đánh giá tư duy"
]

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": _ua.random,
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return s

def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower().strip()

def _safe_filename(title: str) -> str:
    title = unicodedata.normalize("NFC", title).strip()
    title = re.sub(r'[\\/:*?"<>|]', " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title[:100]

def _extract_gdrive_id(url: str) -> str | None:
    # /file/d/<id>/view
    m1 = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
    if m1:
        return m1.group(1)
    # ?id=<id>
    m2 = re.search(r"id=([A-Za-z0-9_-]+)", url)
    if m2:
        return m2.group(1)
    return None

def search_posts(session: requests.Session, query: str, max_pages: int = 4) -> list[tuple[str, str]]:
    """Tìm các bài viết liên quan trên toanmath.com bằng thanh tìm kiếm."""
    results = []
    seen_urls = set()
    
    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"https://toanmath.com/?s={requests.utils.quote(query)}"
        else:
            url = f"https://toanmath.com/page/{page}/?s={requests.utils.quote(query)}"
            
        console.print(f"[dim]  Searching page {page} for '{query}'...[/dim]")
        try:
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 404:
                break
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "lxml")
            
            articles = soup.select("article, h2.entry-title, h3.entry-title, .entry-title")
            page_results_count = 0
            for a in articles:
                link = a.select_one("a[href]")
                if link:
                    href = link["href"]
                    title = link.get_text(strip=True)
                    if href not in seen_urls:
                        # Kiểm tra xem tiêu đề có thực sự liên quan không
                        t_norm = _normalize(title)
                        is_relevant = any(k in t_norm for k in ["đánh giá năng lực", "đánh giá tư duy", "dgnl", "tsa", "đhsp", "hsa", "apt"])
                        if is_relevant:
                            results.append((title, href))
                            seen_urls.add(href)
                            page_results_count += 1
            
            if page_results_count == 0:
                # Không tìm thấy thêm kết quả nào trên trang này
                break
                
            time.sleep(RATE)
        except Exception as e:
            console.print(f"[yellow]  Error page {page}: {e}[/yellow]")
            break
            
    return results

def find_pdf_links(session: requests.Session, post_url: str) -> list[str]:
    """Tìm các link download PDF hoặc Google Drive trong bài viết."""
    pdf_links = []
    try:
        r = session.get(post_url, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True).lower()
            
            # Link PDF trực tiếp
            if href.lower().endswith(".pdf"):
                pdf_links.append(urljoin(post_url, href))
            # Link Google Drive
            elif "drive.google.com" in href or "docs.google.com" in href:
                gdrive_id = _extract_gdrive_id(href)
                if gdrive_id:
                    direct_url = f"https://drive.google.com/uc?export=download&id={gdrive_id}"
                    pdf_links.append(direct_url)
            # Hoặc nút tải về
            elif "download" in text or "tải về" in text or "tải tài liệu" in text:
                if href.lower().endswith(".pdf") or "toanmath.com/toanmath-pdf" in href:
                    pdf_links.append(urljoin(post_url, href))
                    
    except Exception as e:
        console.print(f"[yellow]  Error parsing post {post_url}: {e}[/yellow]")
        
    # Loại bỏ trùng lặp và giữ thứ tự
    return list(dict.fromkeys(pdf_links))

def urljoin(base: str, url: str) -> str:
    from urllib.parse import urljoin as uj
    return uj(base, url)

def download_pdf(session: requests.Session, url: str, dest_path: Path) -> bool:
    """Tải file PDF và xác thực header."""
    headers = {
        "User-Agent": _ua.random,
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        r = session.get(url, headers=headers, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
        
        # Đọc 64 byte đầu
        chunk = next(r.iter_content(64), b"")
        if not chunk.startswith(b"%PDF"):
            # Nếu là link drive.google.com, đôi khi trả về HTML cảnh báo quét virus
            if "drive.google.com" in url or "googleusercontent.com" in url:
                # Thử lấy lại với confirm=t để bỏ qua cảnh báo
                gdrive_id = _extract_gdrive_id(url)
                if gdrive_id:
                    confirm_url = f"https://drive.google.com/uc?export=download&id={gdrive_id}&confirm=t"
                    r = session.get(confirm_url, headers=headers, stream=True, timeout=TIMEOUT)
                    r.raise_for_status()
                    chunk = next(r.iter_content(64), b"")
            
            if not chunk.startswith(b"%PDF"):
                return False
                
        buf = io.BytesIO()
        buf.write(chunk)
        for c in r.iter_content(8192):
            buf.write(c)
            
        dest_path.write_bytes(buf.getvalue())
        return True
    except Exception:
        return False

def run():
    console.print("[bold cyan]=== BẮT ĐẦU CRAWL HÀNG LOẠT ĐỀ THI ĐGNL / ĐGTD ===[/bold cyan]")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Đọc metadata hiện có để tránh tải trùng và giữ lại các đề thi chất lượng cũ
    existing_metadata = []
    existing_ids = set()
    existing_urls = set()
    
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                existing_metadata = json.load(f)
            for item in existing_metadata:
                existing_ids.add(item["id"])
                if "source_url" in item:
                    existing_urls.add(item["source_url"])
            console.print(f"[green]Đã đọc {len(existing_metadata)} đề thi hiện tại từ metadata.[/green]")
        except Exception as e:
            console.print(f"[yellow]Không đọc được metadata hiện tại: {e}. Tạo mới...[/yellow]")
            
    # 2. Tìm kiếm các bài viết liên quan
    session = _session()
    all_posts = []
    seen_post_urls = set()
    
    for q in SEARCH_QUERIES:
        posts = search_posts(session, q, max_pages=15)
        for title, url in posts:
            if url not in seen_post_urls:
                all_posts.append((title, url))
                seen_post_urls.add(url)
                
    console.print(f"[bold green]Tìm thấy {len(all_posts)} bài viết chứa đề thi ĐGNL/ĐGTD trên internet.[/bold green]")
    
    downloaded_count = 0
    new_metadata = []
    
    # 2.5 Tải các link PDF trực tiếp đã định nghĩa trước
    predefined_downloads = [
        {
            "title": "Đề thi thử Đánh giá tư duy Bách Khoa - Đề TSA số 15",
            "url": "https://hsa-education.sgp1.digitaloceanspaces.com/9845cdea-e81f-4b27-9dd4-243ca5daa931_%C4%90%E1%BB%80%20TSA%20S%E1%BB%90%2015.pdf",
            "exam_type": "TSA",
            "year": "2025"
        }
    ]
    for p in predefined_downloads:
        if p["url"] in existing_urls:
            continue
        filename = f"{p['exam_type']}_{p['year']}_{_safe_filename(p['title'])}.pdf"
        dest = OUT_DIR / filename
        console.print(f"\nTải đề thi định nghĩa trước: {p['title']}...")
        ok = download_pdf(session, p["url"], dest)
        if ok:
            downloaded_count += 1
            rel_path = f"data/dgnl/{filename}"
            new_metadata.append({
                "id": f"{p['exam_type'].lower()}_{p['year']}_tsa15",
                "title": p["title"],
                "exam_type": p["exam_type"],
                "year": p["year"],
                "subject": "Tổng hợp",
                "file_path": rel_path,
                "absolute_path": str(dest.resolve()),
                "source_url": p["url"],
                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "file_size_bytes": dest.stat().st_size
            })
            existing_urls.add(p["url"])
            console.print(f"  [green]✓ Tải thành công! ({dest.stat().st_size // 1024} KB)[/green]")
            time.sleep(RATE)
    
    # 3. Duyệt từng bài viết để lấy link PDF và tải về
    
    for idx, (title, post_url) in enumerate(all_posts, 1):
        console.print(f"\n[bold]Bài viết {idx}/{len(all_posts)}: {title}[/bold]")
        console.print(f"  URL: {post_url}")
        
        pdf_urls = find_pdf_links(session, post_url)
        console.print(f"  Tìm thấy {len(pdf_urls)} link tải PDF tiềm năng.")
        
        for p_idx, pdf_url in enumerate(pdf_urls, 1):
            # Tránh tải trùng URL
            if pdf_url in existing_urls:
                console.print(f"  [dim]Link đã được tải trước đó: {pdf_url} (Bỏ qua)[/dim]")
                continue
                
            # Tạo tên file an toàn
            slug = _safe_filename(title)
            # Xác định loại kỳ thi
            exam_type = "ĐGNL"
            t_norm = _normalize(title)
            if "hsa" in t_norm or "hà nội" in t_norm:
                exam_type = "HSA"
            elif "apt" in t_norm or "hồ chí minh" in t_norm or "tphcm" in t_norm:
                exam_type = "APT"
            elif "tsa" in t_norm or "bách khoa" in t_norm:
                exam_type = "TSA"
            elif "sư phạm hà nội" in t_norm or "hnue" in t_norm:
                exam_type = "HNUE"
            elif "sư phạm tp" in t_norm or "hcmue" in t_norm:
                exam_type = "HCMUE"
                
            # Xác định năm
            year = "2025"
            year_match = re.search(r"\b(202[0-7])\b", title)
            if year_match:
                year = year_match.group(1)
                
            filename = f"{exam_type}_{year}_{slug}"
            if len(pdf_urls) > 1:
                filename += f"_part{p_idx}"
            filename += ".pdf"
            
            dest = OUT_DIR / filename
            
            console.print(f"  Đang tải file {p_idx}: {filename}...")
            ok = download_pdf(session, pdf_url, dest)
            if ok:
                downloaded_count += 1
                rel_path = f"data/dgnl/{filename}"
                item_id = f"{exam_type.lower()}_{year}_{slug.lower()}"
                if len(pdf_urls) > 1:
                    item_id += f"_p{p_idx}"
                item_id = re.sub(r"[^a-z0-9_]", "", item_id)
                
                # Lưu metadata
                meta_item = {
                    "id": item_id,
                    "title": f"{title} (File {p_idx})" if len(pdf_urls) > 1 else title,
                    "exam_type": exam_type,
                    "year": year,
                    "subject": "Toán học / Tổng hợp",
                    "file_path": rel_path,
                    "absolute_path": str(dest.resolve()),
                    "source_url": pdf_url,
                    "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "file_size_bytes": dest.stat().st_size
                }
                new_metadata.append(meta_item)
                existing_urls.add(pdf_url)
                console.print(f"  [green]✓ Tải thành công! ({dest.stat().st_size // 1024} KB)[/green]")
            else:
                console.print(f"  [red]✗ Tải thất bại hoặc file không phải PDF hợp lệ.[/red]")
                
            time.sleep(RATE)
            
    # 4. Gộp metadata cũ và mới rồi lưu lại
    combined_metadata = existing_metadata + new_metadata
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(combined_metadata, f, ensure_ascii=False, indent=2)
        console.print(f"\n[bold green]✓ Đã cập nhật metadata mới vào file: {METADATA_FILE.name}[/bold green]")
        console.print(f"Tổng số đề thi ĐGNL/ĐGTD hiện có: {len(combined_metadata)}")
    except Exception as e:
        console.print(f"[bold red]✗ Lỗi khi lưu file metadata: {e}[/bold red]")
        
    console.print(f"\n[bold cyan]=== HOÀN THÀNH: Đã scrape thêm {downloaded_count} đề thi ĐGNL mới! ===[/bold cyan]")

if __name__ == "__main__":
    run()
