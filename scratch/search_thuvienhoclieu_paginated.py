import sys
import io
import requests
import re
import time
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def clean_title(title):
    # Normalize unicode and whitespace
    import unicodedata
    title = unicodedata.normalize("NFC", title)
    return re.sub(r'\s+', ' ', title).strip()

def search_page(query, page):
    url = f"https://thuvienhoclieu.com/page/{page}/?s={query.replace(' ', '+')}"
    print(f"Fetching: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"  -> Page {page} status {r.status_code}")
            return []
        
        soup = BeautifulSoup(r.text, 'html.parser')
        posts = []
        for a in soup.select("h2.entry-title a, h3.entry-title a, .post-title a"):
            title = clean_title(a.get_text(strip=True))
            href = a['href']
            posts.append((title, href))
        return posts
    except Exception as e:
        print(f"  -> Error fetching page {page}: {e}")
        return []

def get_docx_link(page_url):
    try:
        r = requests.get(page_url, headers=headers, timeout=20)
        if r.status_code != 200:
            return ""
        matches = re.findall(
            r'href=["\'](https://thuvienhoclieu\.com/wp-content/uploads/[^"\'<> ]+\.docx)["\']',
            r.text, re.IGNORECASE
        )
        return matches[0] if matches else ""
    except Exception as e:
        return ""

def is_thpt_english_exam(title):
    t = title.lower()
    # Must contain english or tieng anh
    if not ("tiếng anh" in t or "tieng anh" in t or "english" in t or "anh 12" in t):
        return False
        
    # Exclude other grades
    exclude_keywords = [
        "vào 10", "vao 10", "lớp 10", "lop 10", "lớp 11", "lop 11",
        "lớp 9", "lop 9", "lớp 8", "lop 8", "lớp 7", "lop 7",
        "lớp 6", "lop 6", "lớp 5", "lop 5", "lớp 4", "lop 4",
        "lớp 3", "lop 3", "lớp 2", "lop 2", "lớp 1", "lop 1",
        "học kỳ", "hoc ky", "giữa kỳ", "giua ky", "giữa hk", "giua hk",
        "hk1", "hk2"
    ]
    for kw in exclude_keywords:
        if kw in t:
            return False
            
    # Should look like high school trial/prep exam
    include_keywords = [
        "tốt nghiệp", "tot nghiep", "thpt", "quốc gia", "quoc gia", "tn thpt", "ôn thi"
    ]
    return any(kw in t for kw in include_keywords)

def main():
    query = "đề thi thử tốt nghiệp tiếng anh"
    seen_hrefs = set()
    candidates = []
    
    # We will search page 1 to 7
    for page in range(1, 8):
        posts = search_page(query, page)
        if not posts:
            break
        for title, href in posts:
            if href not in seen_hrefs and is_thpt_english_exam(title):
                seen_hrefs.add(href)
                candidates.append((title, href))
        time.sleep(1)
        
    print(f"\nFound {len(candidates)} THPT English candidate exams:")
    valid_count = 0
    final_list = []
    for idx, (title, href) in enumerate(candidates, 1):
        docx = get_docx_link(href)
        if docx:
            valid_count += 1
            final_list.append((title, href, docx))
            print(f"{valid_count:02d}. Title: {title}")
            print(f"    Page: {href}")
            print(f"    DOCX: {docx}")
            print("-" * 50)
            if valid_count >= 15: # Stop once we get 15 solid links
                break
        time.sleep(0.5)

if __name__ == "__main__":
    main()
