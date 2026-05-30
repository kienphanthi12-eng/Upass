import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urljoin
import re

queries = ["đánh giá năng lực", "đánh giá tư duy", "dgnl", "tsa"]
base_url = "https://tailieu365.vn/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

seen_posts = set()
post_details = []

def search_site(query):
    print(f"\nSearching tailieu365.vn for: '{query}'...")
    for page in range(1, 5):
        if page == 1:
            url = f"{base_url}?s={urllib.parse.quote(query)}"
        else:
            url = f"{base_url}page/{page}/?s={urllib.parse.quote(query)}"
            
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 404:
                break
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "lxml")
            
            articles = soup.select("article, h2.entry-title, h3.entry-title, .entry-title, .post-title")
            found = 0
            for a in articles:
                link = a.select_one("a[href]")
                if link:
                    href = link["href"]
                    title = link.get_text(strip=True)
                    if href not in seen_posts and "tailieu365.vn" in href:
                        t_norm = title.lower()
                        if any(k in t_norm for k in ["đánh giá năng lực", "đánh giá tư duy", "dgnl", "tsa", "hsa", "apt"]):
                            seen_posts.add(href)
                            post_details.append((title, href))
                            found += 1
            if found == 0:
                break
        except Exception as e:
            print(f"Error search page {page}: {e}")
            break

for q in queries:
    search_site(q)

print(f"\nFound {len(post_details)} total relevant posts:")
for title, href in post_details:
    print(f" - {title}: {href}")
