"""scraper/crawl_tailieu365.py — Thu thập đề thi ĐGNL / ĐGTD từ tailieu365.vn.

Chạy:
    python scraper/crawl_tailieu365.py
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
RATE = 1.2

SEARCH_QUERIES = [
    "đánh giá năng lực",
    "đánh giá tư duy",
    "dgnl",
    "tsa"
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
    m1 = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
    if m1:
        return m1.group(1)
    m2 = re.search(r"id=([A-Za-z0-9_-]+)", url)
    if m2:
        return m2.group(1)
    return None

def search_articles(session: requests.Session, query: str) -> list[tuple[str, str]]:
    """Tìm kiếm các bài viết liên quan trên tailieu365.vn."""
    results = []
    seen = set()
    
    for page in range(1, 5):
        if page == 1:
            url = f"https://tailieu365.vn/?s={requests.utils.quote(query)}"
        else:
            url = f"https://tailieu365.vn/page/{page}/?s={requests.utils.quote(query)}"
            
        console.print(f"[dim]  Searching page {page} on tailieu365 for '{query}'...[/dim]")
        try:
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 404:
                break
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "lxml")
            
            links = soup.find_all("a", href=True)
            found_count = 0
            for a in links:
                href = a["href"]
                text = a.get_text(strip=True)
                
                # Biến đổi thành absolute URL
                full_url = urljoin("https://tailieu365.vn/", href)
                if "tailieu365.vn" not in full_url:
                    continue
                    
                path = urlparse(full_url).path
                p_lower = path.lower()
                
                # Lọc link bài viết hợp lệ
                if (
                    len(path) > 5
                    and path.endswith("/")
                    and not any(k in p_lower for k in ["/tag/", "/category/", "/page/", "/about", "/contact", "/search", "/tai-lieu-on-thi-dgnl/"])
                ):
                    # Kiểm tra keywords liên quan
                    if any(k in p_lower for k in ["dgnl", "danh-gia", "nang-luc", "tu-duy", "tsa", "hsa", "apt", "vact", "v-act"]):
                        if full_url not in seen:
                            results.append((text or path.strip("/"), full_url))
                            seen.add(full_url)
                            found_count += 1
            
            if found_count == 0:
                break
            time.sleep(RATE)
        except Exception as e:
            console.print(f"[yellow]  Error tailieu365 search page {page}: {e}[/yellow]")
            break
            
    return results

def urljoin(base: str, url: str) -> str:
    from urllib.parse import urljoin as uj
    return uj(base, url)

def urlparse(url: str):
    from urllib.parse import urlparse as up
    return up(url)

def find_gdrive_links(session: requests.Session, article_url: str) -> list[str]:
    """Phân tích bài viết để lấy tất cả link Google Drive."""
    drive_links = []
    try:
        r = session.get(article_url, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "drive.google.com" in href or "docs.google.com" in href:
                gdrive_id = _extract_gdrive_id(href)
                if gdrive_id:
                    direct_url = f"https://drive.google.com/uc?export=download&id={gdrive_id}"
                    drive_links.append(direct_url)
    except Exception as e:
        console.print(f"[yellow]  Lỗi khi đọc bài viết {article_url}: {e}[/yellow]")
    return list(dict.fromkeys(drive_links))

def download_pdf(session: requests.Session, url: str, dest_path: Path) -> bool:
    headers = {
        "User-Agent": _ua.random,
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        r = session.get(url, headers=headers, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
        
        chunk = next(r.iter_content(64), b"")
        if not chunk.startswith(b"%PDF"):
            if "drive.google.com" in url or "googleusercontent.com" in url:
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
    console.print("[bold cyan]=== BẮT ĐẦU SCRAPE TAILIEU365.VN ===[/bold cyan]")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Đọc metadata hiện có
    existing_metadata = []
    existing_urls = set()
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                existing_metadata = json.load(f)
            for item in existing_metadata:
                if "source_url" in item:
                    existing_urls.add(item["source_url"])
            console.print(f"[green]Đã đọc {len(existing_metadata)} đề thi hiện tại từ metadata.[/green]")
        except Exception as e:
            console.print(f"[yellow]Lỗi đọc metadata: {e}[/yellow]")
            
    # 2. Tìm kiếm bài viết
    session = _session()
    all_articles = []
    seen_urls = set()
    
    for q in SEARCH_QUERIES:
        articles = search_articles(session, q)
        for title, url in articles:
            if url not in seen_urls:
                all_articles.append((title, url))
                seen_urls.add(url)
                
    console.print(f"[bold green]Tìm thấy {len(all_articles)} bài viết ĐGNL trên tailieu365.vn.[/bold green]")
    
    # 3. Duyệt bài viết và tải tài liệu
    downloaded_count = 0
    new_metadata = []
    
    for idx, (title, article_url) in enumerate(all_articles, 1):
        console.print(f"\n[bold]Bài viết {idx}/{len(all_articles)}: {title}[/bold]")
        console.print(f"  URL: {article_url}")
        
        gdrive_urls = find_gdrive_links(session, article_url)
        console.print(f"  Tìm thấy {len(gdrive_urls)} link Google Drive tiềm năng.")
        
        # Đọc slug từ URL
        path = urlparse(article_url).path
        slug = path.strip("/").replace("pdf-", "").replace("fdf-", "")
        if not slug:
            slug = f"tailieu365_doc_{idx}"
            
        for g_idx, g_url in enumerate(gdrive_urls, 1):
            if g_url in existing_urls:
                console.print(f"  [dim]Link đã được tải trước đó: {g_url} (Bỏ qua)[/dim]")
                continue
                
            # Phân loại kỳ thi
            exam_type = "ĐGNL"
            s_lower = slug.lower()
            if "hsa" in s_lower or "ha-noi" in s_lower:
                exam_type = "HSA"
            elif "apt" in s_lower or "ho-chi-minh" in s_lower or "vact" in s_lower or "v-act" in s_lower:
                exam_type = "APT"
            elif "tsa" in s_lower or "bach-khoa" in s_lower or "tu-duy" in s_lower:
                exam_type = "TSA"
                
            # Năm
            year = "2025"
            year_match = re.search(r"(202[0-7])", s_lower)
            if year_match:
                year = year_match.group(1)
                
            filename = f"{exam_type}_{year}_{_safe_filename(slug)}"
            if len(gdrive_urls) > 1:
                filename += f"_file{g_idx}"
            filename += ".pdf"
            
            dest = OUT_DIR / filename
            console.print(f"  Đang tải file {g_idx}: {filename}...")
            
            ok = download_pdf(session, g_url, dest)
            if ok:
                downloaded_count += 1
                rel_path = f"data/dgnl/{filename}"
                item_id = f"{exam_type.lower()}_{year}_{slug.lower()}"
                if len(gdrive_urls) > 1:
                    item_id += f"_f{g_idx}"
                item_id = re.sub(r"[^a-z0-9_]", "", item_id)
                
                meta_item = {
                    "id": item_id,
                    "title": f"{title} (File {g_idx})" if len(gdrive_urls) > 1 else title,
                    "exam_type": exam_type,
                    "year": year,
                    "subject": "Tài liệu ôn thi ĐGNL / ĐGTD",
                    "file_path": rel_path,
                    "absolute_path": str(dest.resolve()),
                    "source_url": g_url,
                    "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "file_size_bytes": dest.stat().st_size
                }
                new_metadata.append(meta_item)
                existing_urls.add(g_url)
                console.print(f"  [green]✓ Tải thành công! ({dest.stat().st_size // 1024} KB)[/green]")
            else:
                console.print(f"  [red]✗ Tải thất bại hoặc file không phải PDF hợp lệ.[/red]")
                
            time.sleep(RATE)
            
    # 4. Ghi metadata
    combined_metadata = existing_metadata + new_metadata
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(combined_metadata, f, ensure_ascii=False, indent=2)
        console.print(f"\n[bold green]✓ Cập nhật metadata mới vào file: {METADATA_FILE.name}[/bold green]")
        console.print(f"Tổng số đề thi ĐGNL/ĐGTD hiện có: {len(combined_metadata)}")
    except Exception as e:
        console.print(f"[bold red]✗ Lỗi khi lưu file metadata: {e}[/bold red]")
        
    console.print(f"\n[bold cyan]=== HOÀN THÀNH: Đã tải thêm {downloaded_count} tài liệu ĐGNL mới! ===[/bold cyan]")

if __name__ == "__main__":
    run()
