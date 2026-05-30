import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

urls = [
    "https://toanmath.com/2024/08/de-minh-hoa-danh-gia-nang-luc-mon-toan-nam-2025-truong-dhsp-tp-ho-chi-minh.html",
    "https://toanmath.com/2024/08/de-tham-khao-danh-gia-nang-luc-mon-toan-nam-2025-dai-hoc-quoc-gia-ha-noi.html",
    "https://toanmath.com/2024/11/de-tham-khao-dgnl-mon-toan-xet-tuyen-dai-hoc-2025-truong-dhsp-ha-noi.html",
    "https://toanmath.com/2026/03/tuyen-tap-10-de-thi-thu-ky-thi-danh-gia-tu-duy-dai-hoc-bach-khoa-ha-noi-tsa.html"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

def inspect_article(url):
    print(f"\nInspecting article: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        
        # Print entry title
        title_elem = soup.select_one("h1.entry-title, h1")
        title = title_elem.get_text(strip=True) if title_elem else "No Title"
        print(f"Title: {title}")
        
        # Find all a tags
        links = soup.find_all("a", href=True)
        pdf_links = []
        gdrive_links = []
        other_interesting = []
        
        for a in links:
            href = a["href"]
            text = a.get_text(strip=True)
            if href.lower().endswith(".pdf"):
                pdf_links.append((text, href))
            elif "drive.google.com" in href or "docs.google.com" in href:
                gdrive_links.append((text, href))
            elif any(k in text.lower() or k in href.lower() for k in ["download", "tải", "tai-ve", "link"]):
                other_interesting.append((text, href))
                
        print(f"  Direct PDF links found: {len(pdf_links)}")
        for text, href in pdf_links:
            print(f"    - [{text}]: {href}")
            
        print(f"  Google Drive links found: {len(gdrive_links)}")
        for text, href in gdrive_links:
            print(f"    - [{text}]: {href}")
            
        print(f"  Other links found: {len(other_interesting)}")
        for text, href in other_interesting[:5]:
            print(f"    - [{text}]: {href}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    for url in urls:
        inspect_article(url)
