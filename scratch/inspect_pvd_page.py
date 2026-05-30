import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "https://thpt-phamvandong-khanhhoa.edu.vn/tin-tuc/ke-hoach-ngoai-khoa-tim-hieu-ve-ky-thi-danh-gia-nang-luc-2025.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

try:
    print(f"Fetching: {url}")
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "lxml")
    
    links = soup.find_all("a", href=True)
    print(f"Total links found: {len(links)}")
    for a in links:
        href = a["href"]
        text = a.get_text(strip=True)
        full_url = urljoin(url, href)
        if ".pdf" in href.lower() or "download" in href.lower() or "uploads" in href.lower():
            print(f"Found link: [{text}] -> {full_url}")
            
except Exception as e:
    print(f"Error: {e}")
