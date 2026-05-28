"""scraper/scraper.py — Tự động tìm và tải PDF đề thi THPT môn Toán 2026.

Chạy:
    python scraper/scraper.py                    # tải tối đa 50 đề
    python scraper/scraper.py --count 30         # tải tối đa 30 đề
    python scraper/scraper.py --dry              # chỉ liệt kê, không tải
    python scraper/scraper.py --out data/pdfs    # đổi thư mục lưu
"""
from __future__ import annotations

import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import re
import time
import unicodedata
from pathlib import Path
from typing import Iterator
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from rich.console import Console
from rich.table import Table

# ── Config ────────────────────────────────────────────────────────────────────

OUT_DIR = Path(__file__).parent.parent / "data" / "pdfs"
YEAR    = "2026"
TARGET  = 50
TIMEOUT = 20
RATE    = 1.5   # giây giữa các request

console = Console()
_ua = UserAgent()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": _ua.random,
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return s


def _get(session: requests.Session, url: str, **kw) -> requests.Response | None:
    try:
        r = session.get(url, timeout=TIMEOUT, **kw)
        r.raise_for_status()
        return r
    except Exception as e:
        console.log(f"[yellow]GET fail {url}: {e}[/yellow]")
        return None


def _soup(r: requests.Response) -> BeautifulSoup:
    return BeautifulSoup(r.content, "lxml")


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower().strip()


def _safe_filename(title: str) -> str:
    title = unicodedata.normalize("NFC", title).strip()
    title = re.sub(r'[\\/:*?"<>|]', " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title[:120]


def _is_math_exam(title: str) -> bool:
    t = _normalize(title)
    has_year  = YEAR in t or "2025-2026" in t or "2025 - 2026" in t
    has_subj  = any(k in t for k in ["toán", "toan", "math"])
    has_type  = any(k in t for k in [
        "thi thử", "thi thu", "khảo sát", "khao sat",
        "ôn thi", "on thi", "tốt nghiệp", "tot nghiep", "thpt",
        "tham khảo", "tham khao",
    ])
    is_grade_10_11 = bool(re.search(r"to[aá]n\s*(10|11)\b", t))
    return has_year and has_subj and has_type and not is_grade_10_11


def _existing_titles(out_dir: Path) -> set[str]:
    result = set()
    for f in out_dir.glob("*.pdf"):
        stem = f.stem
        if stem.startswith(YEAR + "_"):
            stem = stem[len(YEAR) + 1:]
        result.add(_normalize(stem))
    return result


def _is_duplicate(title: str, existing: set[str]) -> bool:
    t = _normalize(title)
    if t in existing:
        return True
    words_new = set(t.split())
    for ex in existing:
        words_ex = set(ex.split())
        if not words_new or not words_ex:
            continue
        overlap = len(words_new & words_ex) / max(len(words_new), len(words_ex))
        if overlap >= 0.80:
            return True
    return False


def _download_pdf(
    session: requests.Session,
    url: str,
    title: str,
    out_dir: Path,
    dry: bool,
) -> bool:
    filename = f"{YEAR}_{_safe_filename(title)}.pdf"
    dest = out_dir / filename

    if dest.exists():
        console.log(f"[dim]Đã có: {filename}[/dim]")
        return False

    if dry:
        console.log(f"[cyan][DRY] {filename}[/cyan]")
        return True

    r = _get(session, url, stream=True)
    if not r:
        return False

    ct = r.headers.get("content-type", "")
    if "pdf" not in ct and not url.lower().endswith(".pdf"):
        chunk = next(r.iter_content(64), b"")
        if not chunk.startswith(b"%PDF"):
            console.log(f"[yellow]Không phải PDF: {url}[/yellow]")
            return False
        buf = io.BytesIO(chunk)
        for c in r.iter_content(8192):
            buf.write(c)
        dest.write_bytes(buf.getvalue())
    else:
        dest.write_bytes(r.content)

    size_kb = dest.stat().st_size // 1024
    if size_kb < 20:
        dest.unlink()
        console.log(f"[yellow]File quá nhỏ ({size_kb}KB), bỏ qua: {filename}[/yellow]")
        return False

    console.log(f"[green]✓ {filename} ({size_kb} KB)[/green]")
    return True


def _find_gdrive_pdf(session: requests.Session, gdrive_url: str) -> str | None:
    """Lấy URL tải trực tiếp từ Google Drive share link."""
    # Chuẩn hóa: /file/d/<id>/view → /uc?export=download&id=<id>
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", gdrive_url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return None


# ── Site scrapers ─────────────────────────────────────────────────────────────

class ToanMathScraper:
    """toanmath.com — nguồn chính, nhiều đề thi thử THPT môn Toán miễn phí."""

    name = "toanmath.com"
    base = "https://toanmath.com"
    start_urls = [
        "https://toanmath.com/tag/de-thi-thu-thpt-mon-toan-2026/",
        "https://toanmath.com/de-thi-thu-thpt/",
        "https://toanmath.com/de-khao-sat-mon-toan/",
    ]

    def iter_items(self, session: requests.Session) -> Iterator[tuple[str, str]]:
        seen_posts: set[str] = set()
        for start in self.start_urls:
            page_url: str | None = start
            while page_url:
                r = _get(session, page_url)
                if not r:
                    break
                soup = _soup(r)

                for article in soup.select("article, h2.entry-title, h3.entry-title"):
                    link = article.select_one("a[href]")
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    href  = link["href"]
                    if not href or href in seen_posts:
                        continue
                    if not _is_math_exam(title):
                        continue
                    seen_posts.add(href)
                    pdf_url = self._find_pdf(session, urljoin(self.base, href), title)
                    if pdf_url:
                        yield title, pdf_url
                    time.sleep(RATE)

                next_link = soup.select_one("a.next, a[rel='next'], .nav-previous a, .navigation a:last-child")
                page_url = urljoin(self.base, next_link["href"]) if next_link and next_link.get("href") else None
                time.sleep(RATE)

    def _find_pdf(self, session: requests.Session, post_url: str, title: str) -> str | None:
        r = _get(session, post_url)
        if not r:
            return None
        soup = _soup(r)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                return urljoin(self.base, href)
            if "drive.google.com" in href or "docs.google.com" in href:
                return _find_gdrive_pdf(session, href) or href
        # Tìm trong nội dung text (đôi khi URL nằm trong đoạn text)
        for a in soup.find_all("a", href=True):
            if "download" in a.get("class", []) or "download" in a.get_text(strip=True).lower():
                return urljoin(self.base, a["href"])
        return None


class VndocScraper:
    """vndoc.com — kho tài liệu lớn, nhiều đề thi THPT chính thức từ Sở GD."""

    name = "vndoc.com"
    base = "https://vndoc.com"
    start_urls = [
        "https://vndoc.com/thi-thpt-quoc-gia-mon-toan",
    ]

    def iter_items(self, session: requests.Session) -> Iterator[tuple[str, str]]:
        seen: set[str] = set()
        for start in self.start_urls:
            page_num = 1
            while page_num <= 15:
                page_url = start if page_num == 1 else f"{start}/{page_num}"
                r = _get(session, page_url)
                if not r:
                    break
                soup = _soup(r)

                items_found = 0
                for a in soup.select("h3 a[href], h2 a[href], .item-doc a[href], .post-item a[href]"):
                    href  = a.get("href", "")
                    title = a.get_text(strip=True)
                    if not href or href in seen or not title:
                        continue
                    if not _is_math_exam(title):
                        continue
                    seen.add(href)
                    items_found += 1
                    full = urljoin(self.base, href)
                    pdf_url = self._find_pdf(session, full)
                    if pdf_url:
                        yield title, pdf_url
                    time.sleep(RATE)

                if items_found == 0:
                    break
                page_num += 1
                time.sleep(RATE)

    def _find_pdf(self, session: requests.Session, post_url: str) -> str | None:
        r = _get(session, post_url)
        if not r:
            return None
        soup = _soup(r)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                return urljoin(self.base, href)
            if "drive.google.com" in href:
                return _find_gdrive_pdf(session, href) or href
        # Nút tải về
        for a in soup.find_all("a", href=True):
            cls = " ".join(a.get("class", []))
            if "download" in cls.lower() or "tai-ve" in cls.lower():
                return urljoin(self.base, a["href"])
        return None


class MathVNScraper:
    """mathvn.com — blog Toán Học Việt Nam, nhiều đề thi thử với PDF/GDrive."""

    name = "mathvn.com"
    base = "https://www.mathvn.com"
    # Trang tổng hợp đề thi thử
    start_url = "https://www.mathvn.com/p/de-thi-thu-toan.html"
    # Blogger label search
    label_url = "https://www.mathvn.com/search/label/%C4%91%E1%BB%81+thi+th%E1%BB%AD+THPT"

    def iter_items(self, session: requests.Session) -> Iterator[tuple[str, str]]:
        seen: set[str] = set()
        # 1) Trang tổng hợp cố định
        for url in [self.start_url]:
            r = _get(session, url)
            if r:
                yield from self._parse_listing(session, _soup(r), seen)

        # 2) Trang năm 2026 (Blogger archive)
        for month in range(1, 7):
            archive_url = f"https://www.mathvn.com/{YEAR}/{month:02d}/"
            r = _get(session, archive_url)
            if not r:
                continue
            soup = _soup(r)
            for a in soup.select("h3.post-title a[href], h2.post-title a[href], .entry-title a[href]"):
                href  = a.get("href", "")
                title = a.get_text(strip=True)
                if not href or href in seen or not _is_math_exam(title):
                    continue
                seen.add(href)
                pdf_url = self._find_pdf(session, href)
                if pdf_url:
                    yield title, pdf_url
                time.sleep(RATE)
            time.sleep(RATE)

    def _parse_listing(
        self, session: requests.Session, soup: BeautifulSoup, seen: set[str]
    ) -> Iterator[tuple[str, str]]:
        for a in soup.find_all("a", href=True):
            href  = a.get("href", "")
            title = a.get_text(strip=True)
            if (
                not href
                or href in seen
                or self.base not in href
                or not _is_math_exam(title)
            ):
                continue
            seen.add(href)
            pdf_url = self._find_pdf(session, href)
            if pdf_url:
                yield title, pdf_url
            time.sleep(RATE)

    def _find_pdf(self, session: requests.Session, post_url: str) -> str | None:
        r = _get(session, post_url)
        if not r:
            return None
        soup = _soup(r)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                return href
            if "drive.google.com" in href or "docs.google.com" in href:
                return _find_gdrive_pdf(session, href) or href
        return None


class VietJackScraper:
    """vietjack.com — kho đề thi thử THPT lớn, 100+ đề môn Toán 2026."""

    name = "vietjack.com"
    base = "https://vietjack.com"
    start_url = "https://vietjack.com/on-thi-dai-hoc/de-thi-thu-tot-nghiep-toan-2024.jsp"

    def iter_items(self, session: requests.Session) -> Iterator[tuple[str, str]]:
        r = _get(session, self.start_url)
        if not r:
            return
        soup = _soup(r)
        seen: set[str] = set()

        for a in soup.find_all("a", href=True):
            href  = a["href"]
            title = a.get_text(strip=True)
            if not href or href in seen or not _is_math_exam(title):
                continue
            full = urljoin(self.base, href)
            if "vietjack.com" not in full:
                continue
            seen.add(href)
            pdf_url = self._find_pdf(session, full)
            if pdf_url:
                yield title, pdf_url
            time.sleep(RATE)

    def _find_pdf(self, session: requests.Session, post_url: str) -> str | None:
        r = _get(session, post_url)
        if not r:
            return None
        soup = _soup(r)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                return urljoin(self.base, href)
            if "drive.google.com" in href:
                return _find_gdrive_pdf(session, href) or href
        return None


class SoGDScraper:
    """URL trực tiếp đến PDF đề thi chính thức của Sở GD&ĐT các tỉnh."""

    name = "so-gd-tinh"
    # Thêm (title, pdf_url) khi biết link trực tiếp
    known_pdfs: list[tuple[str, str]] = []

    def iter_items(self, session: requests.Session) -> Iterator[tuple[str, str]]:
        for title, url in self.known_pdfs:
            if _is_math_exam(title):
                yield title, url


# ── Main runner ───────────────────────────────────────────────────────────────

def run_scraper(
    out_dir: Path = OUT_DIR,
    target: int = TARGET,
    dry: bool = False,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = _existing_titles(out_dir)
    console.print(f"[bold]Scraper THPT Toán {YEAR}[/bold] — mục tiêu: {target} đề mới")
    console.print(f"Đã có {len(existing)} PDF trong {out_dir}\n")

    scrapers = [
        ToanMathScraper(),
        VndocScraper(),
        MathVNScraper(),
        VietJackScraper(),
        SoGDScraper(),
    ]

    downloaded = 0
    skipped    = 0
    failed     = 0
    results: list[dict] = []

    session = _session()

    for scraper in scrapers:
        if downloaded >= target:
            break
        console.rule(f"[bold blue]{scraper.name}[/bold blue]")

        try:
            for title, pdf_url in scraper.iter_items(session):
                if downloaded >= target:
                    break

                if _is_duplicate(title, existing):
                    skipped += 1
                    console.log(f"[dim]Trùng: {title[:60]}[/dim]")
                    continue

                ok = _download_pdf(session, pdf_url, title, out_dir, dry)
                if ok:
                    downloaded += 1
                    existing.add(_normalize(title))
                    results.append({"title": title, "url": pdf_url, "status": "✓"})
                else:
                    failed += 1
                    results.append({"title": title, "url": pdf_url, "status": "✗"})

                time.sleep(RATE)

        except KeyboardInterrupt:
            console.print("\n[yellow]Dừng sớm theo yêu cầu.[/yellow]")
            break
        except Exception as e:
            console.log(f"[red]Scraper {scraper.name} lỗi: {e}[/red]")

    # Tổng kết
    console.rule("[bold]Kết quả[/bold]")
    table = Table(show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Tên đề", style="cyan")
    table.add_column("Status", width=6)

    for i, r in enumerate(results, 1):
        color = "green" if r["status"] == "✓" else "red"
        table.add_row(str(i), r["title"][:70], f"[{color}]{r['status']}[/{color}]")

    console.print(table)
    console.print(
        f"\nTải thành công: [green]{downloaded}[/green] | "
        f"Bỏ qua (trùng): [dim]{skipped}[/dim] | "
        f"Thất bại: [red]{failed}[/red]"
    )
    return downloaded


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper đề thi THPT Toán 2026")
    parser.add_argument("--count", type=int, default=TARGET,  help="Số đề cần tải (mặc định 50)")
    parser.add_argument("--out",   type=Path, default=OUT_DIR, help="Thư mục lưu PDF")
    parser.add_argument("--dry",   action="store_true",        help="Chỉ liệt kê, không tải")
    args = parser.parse_args()

    n = run_scraper(out_dir=args.out, target=args.count, dry=args.dry)
    sys.exit(0 if n > 0 else 1)
