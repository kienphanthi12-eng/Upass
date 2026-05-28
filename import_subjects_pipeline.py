"""
import_subjects_pipeline.py — Unified Multi-Subject Pipeline (Lý, Hóa, Sử, Anh)
Uses Word COM conversion -> MinerU PDF OCR -> DeepSeek V3 -> Supabase
Inserts 3 exams per subject (12 exams total)
"""
import asyncio
import os
import re
import sys
import io
import time
import requests
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel

# Fix console encoding
if sys.platform == "win32" and hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8" and not getattr(sys.stdout, "_custom_utf8", False):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._custom_utf8 = True
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
import config
from database import db
from processor.ocr import MinerUClient
from import_exam_deepseek import run_pipeline

console = Console()

# ─── Configuration ───────────────────────────────────────────────────────────
PDF_DIR = Path("data/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)
MINERU_DIR = Path("C:/Users/HP/MinerU")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

SUBJECTS = {
    'LY':  {'id': 2, 'name': 'Vật Lý',     'target': 3},
    'HOA': {'id': 3, 'name': 'Hóa Học',     'target': 3},
    'SU':  {'id': 6, 'name': 'Lịch Sử',     'target': 3},
    'ANH': {'id': 9, 'name': 'Tiếng Anh',   'target': 3},
}

CANDIDATE_URLS = {
    'LY': [
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-lam-dong-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-dong-nai-lan-1-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-ca-mau-lan-1-giai-chi-tiet/',
    ],
    'HOA': [
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-lam-dong-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-phu-tho-lan-2-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-da-nang-lan-1-giai-chi-tiet/',
    ],
    'SU': [
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-lam-dong-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-thpt-2026-lich-su-so-gd-phu-tho-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-da-nang-lan-1-giai-chi-tiet/',
    ],
    'ANH': [
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-can-tho-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-lam-dong-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-an-giang-giai-chi-tiet/',
    ],
}

CITY_POOL = [
    "Busan","Hanoi","Ho Chi Minh","Shanghai","Beijing","Hong Kong",
    "Karachi","Johannesburg","London","Warsaw","Budapest","Stockholm",
    "Oslo","Helsinki","Dublin","Vienna","Prague","Athens","Lisbon","Copenhagen",
    "Brussels","Amsterdam","Zurich","Geneva","Milan","Rome","Barcelona","Madrid",
    "Berlin","Munich","Paris","Lyon","Marseille","Toronto","Vancouver","Montreal",
    "New York","Los Angeles","Chicago","Houston","Phoenix","Philadelphia","Seattle",
    "Boston","Miami","Atlanta","Denver","Dallas","San Francisco","Portland"
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_used_cities() -> set:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT display_title FROM exams WHERE display_title IS NOT NULL")
            return {r[0] for r in cur.fetchall()}

def assign_city(used_cities: set) -> str:
    for city in CITY_POOL:
        if city not in used_cities:
            return city
    return f"City_{len(used_cities)}"

def set_city(exam_id: int, city: str) -> None:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE exams SET display_title = %s WHERE id = %s", (city, exam_id))

def exam_title_exists(title: str) -> bool:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM exams WHERE title = %s LIMIT 1", (title,))
            return bool(cur.fetchone())

def scrape_docx_url(page_url: str) -> str:
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return ""
        matches = re.findall(
            r'href=["\'](https://thuvienhoclieu\.com/wp-content/uploads/[^"\'<> ]+\.docx)["\']',
            r.text, re.IGNORECASE
        )
        return matches[0] if matches else ""
    except Exception as e:
        console.print(f"    [red]Error scraping {page_url}: {e}[/]")
        return ""

def download_file(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code != 200:
            return False
        dest.write_bytes(r.content)
        size_kb = dest.stat().st_size // 1024
        console.print(f"    Downloaded: {dest.name} ({size_kb} KB)")
        return True
    except Exception as e:
        console.print(f"    [red]Error downloading {url}: {e}[/]")
        return False

def convert_docx_to_pdf(docx_path: Path, pdf_path: Path) -> bool:
    abs_docx = str(docx_path.resolve())
    abs_pdf = str(pdf_path.resolve())
    console.print(f"    [yellow]Word COM conversion: {docx_path.name} -> {pdf_path.name}...[/]")
    
    ps_cmd = (
        f"$word = New-Object -ComObject Word.Application; "
        f"$word.Visible = $false; "
        f"$doc = $word.Documents.Open('{abs_docx}'); "
        f"$doc.SaveAs('{abs_pdf}', 17); "
        f"$doc.Close(); "
        f"$word.Quit();"
    )
    
    try:
        res = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if res.returncode == 0 and pdf_path.exists():
            console.print("    [green]✓ Word COM conversion successful![/]")
            return True
        else:
            console.print(f"    [red]Word COM failed (code {res.returncode}): {res.stderr or res.stdout}[/]")
            return False
    except Exception as e:
        console.print(f"    [red]Word COM exception: {e}[/]")
        return False

def find_existing_mineru_folder(pdf_name: str) -> Path | None:
    if not MINERU_DIR.exists():
        return None
    candidates = sorted([
        d for d in MINERU_DIR.iterdir()
        if d.is_dir() and d.name.startswith(pdf_name) and (d / "full.md").exists()
    ], key=lambda d: (d / "full.md").stat().st_size, reverse=True)
    return candidates[0] if candidates else None

def call_mineru_api(pdf_path: Path) -> Path | None:
    client = MinerUClient()
    console.print(f"    [yellow]Calling MinerU API for {pdf_path.name}...[/]")
    try:
        info = client.request_upload_url(
            pdf_path.name,
            enable_formula=True,
            enable_table=True,
            is_ocr=True,
            language="ch",
        )
        batch_id   = info["batch_id"]
        upload_url = info["upload_url"]
        
        client.upload_file(upload_url, str(pdf_path))
        
        console.print("    [yellow]Waiting for OCR...[/]")
        result = client.poll_batch(batch_id, timeout=600, interval=8)
        
        folder_name = f"{pdf_path.name}-{batch_id}"
        folder = MINERU_DIR / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        
        markdown = client.download_markdown(result, image_dir=str(folder / "images"))
        (folder / "full.md").write_text(markdown, encoding="utf-8")
        console.print(f"    [green]✓ MinerU OCR success: {len(markdown):,} chars[/]")
        return folder
    except Exception as e:
        console.print(f"    [red]MinerU OCR failed: {e}[/]")
        return None

def build_exam_title(page_url: str, subject_name: str) -> str:
    slug = page_url.rstrip('/').split('/')[-1]
    slug = re.sub(r'-giai-chi-tiet$', '', slug)
    slug = re.sub(r'-co-loi-giai$', '', slug)
    parts = slug.replace('-', ' ').title()
    if '2026' not in parts:
        parts = f"{parts} 2026"
    # Format: 2026_De Thi Thu Tot Nghiep Vat Li 2026 So Gd Lam Dong
    # Simplify to ascii and standard format
    import unicodedata
    def strip_accents(s):
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    clean = strip_accents(parts)
    # Remove thuvienhoclieu site details
    clean = clean.replace("Thuvienhoclieu Com", "").replace("Thuvienhoclieu", "").strip()
    clean = re.sub(r'\s+', ' ', clean)
    return f"2026_{clean.replace(' ', '_')}"

# ─── Main Pipeline ───────────────────────────────────────────────────────────

async def process_exam(page_url: str, subject_code: str):
    info = SUBJECTS[subject_code]
    subject_id = info['id']
    subject_name = info['name']
    
    console.print(f"\n[bold cyan]▶ Scrape & Import: {page_url} ({subject_name})[/]")
    
    # 1. Scrape DOCX URL
    docx_url = scrape_docx_url(page_url)
    if not docx_url:
        console.print("    [red]No DOCX URL found on page.[/]")
        return False
        
    title = build_exam_title(page_url, subject_name)
    console.print(f"    Title: [bold]{title}[/]")
    
    # Check duplicate
    if exam_title_exists(title):
        console.print("    [dim]→ Exam already exists in DB, skipping.[/]")
        return True
        
    # 2. Download DOCX
    docx_name = docx_url.split("/")[-1]
    docx_path = PDF_DIR / docx_name
    if not docx_path.exists():
        ok = download_file(docx_url, docx_path)
        if not ok:
            return False
            
    # 3. Convert DOCX to PDF
    pdf_path = docx_path.with_suffix(".pdf")
    if not pdf_path.exists():
        ok = convert_docx_to_pdf(docx_path, pdf_path)
        if not ok:
            return False
            
    # 4. MinerU OCR
    mineru_folder = find_existing_mineru_folder(pdf_path.name)
    if mineru_folder:
        console.print(f"    [dim]→ Using existing MinerU OCR folder: {mineru_folder.name}[/]")
    else:
        mineru_folder = call_mineru_api(pdf_path)
        if not mineru_folder:
            return False
            
    # 5. DeepSeek Pipeline
    try:
        await run_pipeline(mineru_folder, title, 2026, subject_id)
    except Exception as e:
        console.print(f"    [red]DeepSeek Pipeline failed: {e}[/]")
        return False
        
    # 6. Assign City Display Title
    try:
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM exams WHERE title = %s ORDER BY id DESC LIMIT 1", (title,))
                row = cur.fetchone()
        if row:
            exam_id = row[0]
            used_cities = get_used_cities()
            city = assign_city(used_cities)
            set_city(exam_id, city)
            console.print(f"    [green]✓ Assigned display_title (city codename): {city} to exam_id={exam_id}[/]")
            return True
    except Exception as e:
        console.print(f"    [red]Failed to assign city: {e}[/]")
        
    return False

async def main():
    console.rule("[bold magenta]Unified Multi-Subject THPT 2026 Import Pipeline[/]")
    db.init_pool()
    
    results = []
    for code, info in SUBJECTS.items():
        console.rule(f"[bold yellow]Subject: {info['name']}[/]")
        urls = CANDIDATE_URLS[code]
        for url in urls:
            success = await process_exam(url, code)
            results.append({'url': url, 'subject': info['name'], 'status': '✓' if success else '✗'})
            time.sleep(3) # politeness delay
            
    console.rule("[bold green]Execution Summary[/]")
    for r in results:
        status_color = "green" if r['status'] == '✓' else "red"
        console.print(f"  [{status_color}]{r['status']}[/] | {r['subject']} | {r['url']}")

if __name__ == "__main__":
    asyncio.run(main())
