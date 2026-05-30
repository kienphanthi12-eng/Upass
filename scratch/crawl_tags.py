import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

tags = [
    "danh-gia-nang-luc",
    "de-thi-danh-gia-nang-luc",
    "danh-gia-tu-duy",
    "de-thi-danh-gia-tu-duy",
    "de-thi-dgnl",
    "tsa"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

for tag in tags:
    url = f"https://toanmath.com/tag/{tag}/"
    print(f"\nChecking tag page: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  Status code: {r.status_code}")
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "lxml")
            links = soup.find_all("a", href=True)
            print(f"  Found {len(links)} links.")
            seen = set()
            for a in links:
                href = a["href"]
                text = a.get_text(strip=True)
                if "/20" in href and href.endswith(".html") and href not in seen:
                    print(f"    - {text[:50]} -> {href}")
                    seen.add(href)
    except Exception as e:
        print(f"  Error checking tag {tag}: {e}")
