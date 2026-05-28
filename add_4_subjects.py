"""
add_4_subjects.py — Scrape + import 3 đề mỗi môn: Lý, Hóa, Sử, Anh

Nguồn: thuvienhoclieu.com (DOCX trực tiếp, không cần OCR)
Mục tiêu: 12 đề mới (3 × 4 môn) lên giao diện web
"""
import asyncio
import re
import sys
import io
import time
import requests
from pathlib import Path
from typing import Optional, List

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from database import db
from import_exam_docx import run_docx_pipeline
from rich.console import Console
from rich.panel import Panel

console = Console()

# ─── Cấu hình ────────────────────────────────────────────────────────────────

DATA_DIR = Path("data/pdfs")
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer": "https://thuvienhoclieu.com/",
}

# Subject IDs
SUBJECTS = {
    'LY':  {'id': 2, 'name': 'Vật Lý',     'target': 3},
    'HOA': {'id': 3, 'name': 'Hóa Học',     'target': 3},
    'SU':  {'id': 6, 'name': 'Lịch Sử',     'target': 3},
    'ANH': {'id': 9, 'name': 'Tiếng Anh',   'target': 3},
}

# Candidate exam pages (thuvienhoclieu.com) — ordered by preference
CANDIDATE_URLS = {
    'LY': [
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-lam-dong-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-dong-nai-lan-1-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-ca-mau-lan-1-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-ha-tinh-lan-2-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-vinh-long-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-vat-li-2026-so-gd-son-la-lan-3-giai-chi-tiet/',
    ],
    'HOA': [
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-lam-dong-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-phu-tho-lan-2-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-da-nang-lan-1-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-mon-hoa-2026-so-gd-ha-noi-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-ha-tinh-lan-1-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-hai-phong-lan-1-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-mon-hoa-so-gd-thanh-hoa-lan-2-giai-chi-tiet/',
    ],
    'SU': [
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-lam-dong-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-thpt-2026-lich-su-so-gd-phu-tho-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-da-nang-lan-1-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-dien-bien-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-vinh-long-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-gia-lai-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-nghe-an-lan-3-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-lich-su-so-gd-thanh-hoa-lan-2-giai-chi-tiet/',
    ],
    'ANH': [
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-can-tho-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-lam-dong-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-an-giang-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-thanh-hoa-lan-2-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-tieng-anh-so-gd-ha-tinh-lan-1-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-dong-nai-lan-2-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-nghe-an-lan-2-giai-chi-tiet/',
        'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-2026-tieng-anh-so-gd-ha-noi-lan-1-co-loi-giai/',
    ],
}

# City pool cho display_title
CITY_POOL = [
    "Busan","Hanoi","Ho Chi Minh","Shanghai","Beijing","Hong Kong",
    "Karachi","Johannesburg","London","Warsaw","Budapest","Stockholm",
    "Oslo","Helsinki","Dublin","Vienna","Prague","Athens","Lisbon","Copenhagen",
    "Brussels","Amsterdam","Zurich","Geneva","Milan","Rome","Barcelona","Madrid",
    "Berlin","Munich","Paris","Lyon","Marseille","Toronto","Vancouver","Montreal",
    "New York","Los Angeles","Chicago","Houston","Phoenix","Philadelphia","Seattle",
    "Boston","Miami","Atlanta","Denver","Dallas","San Francisco","Portland",
    "Mexico City","Bogota","Lima","Santiago","Buenos Aires","Sao Paulo","Rio",
    "Lagos","Nairobi","Cairo","Casablanca","Tunis","Accra","Dakar","Addis Ababa",
    "Dubai","Abu Dhabi","Riyadh","Tehran","Istanbul","Ankara","Baku","Tbilisi",
    "Almaty","Tashkent","Bishkek","Ulaanbaatar","Tokyo","Osaka","Seoul","Busan 2",
    "Taipei","Bangkok","Singapore","Kuala Lumpur","Jakarta","Manila","Hanoi 2",
    "Kathmandu","Colombo","Dhaka","Yangon","Phnom Penh","Vientiane","Brunei",
    "Wellington","Sydney","Melbourne","Brisbane","Auckland","Suva","Noumea",
    "Reykjavik","Tallinn","Riga","Vilnius","Minsk","Kyiv","Chisinau","Yerevan",
    "Sarajevo","Zagreb","Ljubljana","Skopje","Tirana","Sofia","Bucharest","Belgrade",
    "Bern","Luxembourg","Valletta","Monaco","Andorra","San Marino","Vatican",
    "Nassau","Kingston","Havana","San Jose","Managua","Tegucigalpa","Guatemala",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_used_cities() -> set:
    """Lấy danh sách city đã dùng từ DB."""
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT display_title FROM exams WHERE display_title IS NOT NULL")
            return {r[0] for r in cur.fetchall()}


def assign_city(used_cities: set) -> str:
    """Lấy city chưa dùng tiếp theo."""
    for city in CITY_POOL:
        if city not in used_cities:
            return city
    return f"City_{len(used_cities)}"


def title_exists(title: str) -> bool:
    """Kiểm tra đề đã tồn tại trong DB."""
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM exams WHERE title = %s LIMIT 1", (title,))
            return bool(cur.fetchone())


def extract_page_title(html: str) -> str:
    """Lấy tiêu đề từ trang HTML."""
    # Try <h1>
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if m:
        t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if t:
            return t
    # Try <title>
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if m:
        t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        t = re.sub(r'\s*[-|–]\s*.*$', '', t)  # remove site name after dash
        return t
    return ''


def scrape_docx_url(page_url: str) -> Optional[str]:
    """Scrape URL file .docx từ trang thuvienhoclieu.com."""
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            console.print(f"    [red]HTTP {r.status_code}[/]")
            return None
        # Tìm link .docx trong HTML
        matches = re.findall(
            r'href=["\']'
            r'(https://thuvienhoclieu\.com/wp-content/uploads/[^"\'<> ]+\.docx)'
            r'["\']',
            r.text, re.IGNORECASE
        )
        if not matches:
            console.print(f"    [yellow]Không tìm thấy DOCX link[/]")
            return None
        return matches[0]
    except Exception as e:
        console.print(f"    [red]Lỗi scrape: {e}[/]")
        return None


def download_docx(url: str, dest: Path) -> bool:
    """Download file DOCX về máy."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        if r.status_code != 200:
            return False
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        size_kb = dest.stat().st_size // 1024
        console.print(f"    Downloaded: {dest.name} ({size_kb} KB)")
        return True
    except Exception as e:
        console.print(f"    [red]Lỗi download: {e}[/]")
        return False


def build_exam_title(page_url: str, subject_name: str) -> str:
    """Tạo tiêu đề đề thi từ URL trang."""
    slug = page_url.rstrip('/').split('/')[-1]
    # Bỏ '-giai-chi-tiet' ở cuối
    slug = re.sub(r'-giai-chi-tiet$', '', slug)
    # Bỏ '-co-loi-giai$'
    slug = re.sub(r'-co-loi-giai$', '', slug)
    # Chuyển slug → title
    parts = slug.replace('-', ' ').title()
    # Thêm năm và môn nếu chưa có
    if '2026' not in parts:
        parts = f"{parts} 2026"
    return f"2026_{parts}"


def set_city(exam_id: int, city: str) -> None:
    """Gán city name cho exam."""
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE exams SET display_title = %s WHERE id = %s",
                (city, exam_id)
            )


# ─── Main ─────────────────────────────────────────────────────────────────────

def run():
    console.rule("[bold cyan]Add 4 Subjects — 3 đề × 4 môn[/]")

    used_cities = get_used_cities()
    total_added = 0
    results = []

    for code, info in SUBJECTS.items():
        subject_id = info['id']
        subject_name = info['name']
        target = info['target']
        candidates = CANDIDATE_URLS[code]

        console.rule(f"[bold]{subject_name}[/] (subject_id={subject_id})")
        added_this = 0

        for page_url in candidates:
            if added_this >= target:
                break

            console.print(f"\n[{added_this+1}/{target}] {page_url}")

            # --- Scrape DOCX URL
            docx_url = scrape_docx_url(page_url)
            if not docx_url:
                continue

            # --- Build title từ URL
            title = build_exam_title(page_url, subject_name)

            # --- Kiểm tra duplicate
            if title_exists(title):
                console.print(f"  [dim]→ Đề đã tồn tại, bỏ qua[/]")
                added_this += 1  # count as done
                continue

            # --- Download DOCX
            fname = re.sub(r'[^\w\-.]', '_', docx_url.split('/')[-1])
            docx_dest = DATA_DIR / fname
            if docx_dest.exists():
                console.print(f"  [dim]→ Đã có file: {fname}[/]")
            else:
                ok = download_docx(docx_url, docx_dest)
                if not ok:
                    continue

            # --- Run pipeline
            try:
                exam_id = run_docx_pipeline(
                    docx_path=str(docx_dest),
                    title=title,
                    year=2026,
                    subject_id=subject_id,
                )
            except Exception as e:
                console.print(f"  [red]Pipeline lỗi: {e}[/]")
                # Cleanup file nếu lỗi
                if docx_dest.exists():
                    docx_dest.unlink()
                continue

            # --- Assign city
            city = assign_city(used_cities)
            set_city(exam_id, city)
            used_cities.add(city)

            console.print(f"  [green]✓ exam_id={exam_id} | city={city}[/]")
            results.append({'exam_id': exam_id, 'subject': subject_name, 'city': city, 'title': title})
            added_this += 1
            total_added += 1
            time.sleep(2)  # polite delay

        if added_this < target:
            console.print(f"  [yellow]⚠ Chỉ thêm được {added_this}/{target} đề {subject_name}[/]")

    # Summary
    console.rule("[bold green]Tổng kết[/]")
    console.print(f"Đã thêm: {total_added} đề mới")
    for r in results:
        console.print(f"  exam_id={r['exam_id']} | {r['subject']} | city={r['city']}")
    console.print("\n[bold]Kiểm tra web: https://upass.io.vn/exams[/]")


if __name__ == '__main__':
    run()
