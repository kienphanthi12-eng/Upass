import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup

url = "https://tailieu365.vn/?s=đánh+giá+năng+lực"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

try:
    print(f"Fetching search page: {url}")
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "lxml")
    
    # Print the title of the search page
    print(f"Page Title: {soup.title.get_text(strip=True) if soup.title else 'No Title'}")
    
    # Print some info about body
    print(f"Body length: {len(r.text)}")
    
    # Find all links on the search results page
    links = soup.find_all("a", href=True)
    print(f"Total links found: {len(links)}")
    
    found_articles = 0
    for a in links:
        href = a["href"]
        text = a.get_text(strip=True)
        h_lower = href.lower()
        if any(k in h_lower for k in ["dgnl", "danh-gia", "nang-luc", "tu-duy", "tsa", "hsa", "apt"]):
            print(f"  Matched link: [{text[:50]}] -> {href}")
            found_articles += 1
            
    print(f"Filtered article links: {found_articles}")
    
except Exception as e:
    print(f"Error: {e}")
