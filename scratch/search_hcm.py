import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
import urllib.parse

def search_toanmath(query):
    print(f"Searching toanmath.com for: '{query}'...")
    url = f"https://toanmath.com/?s={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        
        articles = soup.select("article, h2.entry-title, h3.entry-title, .entry-title")
        results = []
        for a in articles:
            link = a.select_one("a[href]")
            if link:
                href = link["href"]
                title = link.get_text(strip=True)
                if href not in [r[1] for r in results]:
                    results.append((title, href))
        return results
    except Exception as e:
        print(f"Error searching for '{query}': {e}")
        return []

if __name__ == "__main__":
    queries = ["hcm", "hồ chí minh", "đại học quốc gia", "đhqg", "đáp án đánh giá năng lực"]
    for q in queries:
        res = search_toanmath(q)
        print(f"Found {len(res)} results:")
        for title, href in res[:15]:
            print(f" - {title}: {href}")
        print("-" * 50)
