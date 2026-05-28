import sys
import io
import requests
import re
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def search_thuvienhoclieu(query):
    print(f"Searching for '{query}'...")
    url = f"https://thuvienhoclieu.com/?s={query.replace(' ', '+')}"
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"Error {r.status_code}")
            return []
        
        soup = BeautifulSoup(r.text, 'html.parser')
        posts = []
        # In thuvienhoclieu, post links are usually inside h2 or h3 with class entry-title
        for a in soup.select("h2.entry-title a, h3.entry-title a, .post-title a"):
            title = a.get_text(strip=True)
            href = a['href']
            # Only keep posts that look like 2025 or 2026 trial exams for English
            if "anh" in title.lower() or "english" in title.lower():
                posts.append((title, href))
        return posts
    except Exception as e:
        print(f"Search error: {e}")
        return []

def get_docx_link(page_url):
    try:
        r = requests.get(page_url, headers=headers, timeout=20)
        if r.status_code != 200:
            return ""
        # Find any link to .docx
        matches = re.findall(
            r'href=["\'](https://thuvienhoclieu\.com/wp-content/uploads/[^"\'<> ]+\.docx)["\']',
            r.text, re.IGNORECASE
        )
        return matches[0] if matches else ""
    except Exception as e:
        print(f"Scrape error for {page_url}: {e}")
        return ""

def main():
    queries = [
        "đề thi thử tốt nghiệp tiếng anh 2026",
        "đề ôn thi tốt nghiệp tiếng anh 2026",
        "đề thi thử tốt nghiệp tiếng anh 2025"
    ]
    
    all_results = []
    seen_hrefs = set()
    
    for q in queries:
        results = search_thuvienhoclieu(q)
        for title, href in results:
            if href not in seen_hrefs:
                seen_hrefs.add(href)
                all_results.append((title, href))
                
    print(f"\nFound {len(all_results)} unique English exam pages:")
    for idx, (title, href) in enumerate(all_results, 1):
        docx_link = get_docx_link(href)
        print(f"{idx:02d}. Title: {title}")
        print(f"    Page: {href}")
        print(f"    DOCX: {docx_link if docx_link else '[No DOCX found]'}")
        print("-" * 60)

if __name__ == "__main__":
    main()
