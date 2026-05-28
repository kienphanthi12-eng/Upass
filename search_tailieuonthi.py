import sys, io, requests, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from bs4 import BeautifulSoup
from urllib.parse import urljoin

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def search_subject(subject_query):
    # Search on tailieuonthi.org
    url = f"https://tailieuonthi.org/?s={subject_query}"
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"Error searching {subject_query}: {r.status_code}")
            return []
        
        soup = BeautifulSoup(r.text, 'lxml')
        links = []
        for a in soup.select("h2.entry-title a[href], h3.entry-title a[href], .post-title a[href]"):
            title = a.get_text(strip=True)
            href = a['href']
            links.append((title, href))
        return links
    except Exception as e:
        print(f"Error: {e}")
        return []

def get_pdf_download_link(page_url):
    try:
        r = requests.get(page_url, headers=headers, timeout=20)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'lxml')
        
        # Look for direct .pdf links or Google Drive links
        for a in soup.find_all("a", href=True):
            href = a['href']
            text = a.get_text(strip=True).lower()
            if href.lower().endswith(".pdf"):
                return href
            if "drive.google.com" in href:
                return href
            if "download" in text or "tải" in text:
                if href.lower().endswith(".pdf") or "drive.google.com" in href:
                    return href
        return None
    except Exception as e:
        print(f"Error scraping page {page_url}: {e}")
        return None

# Search for Vật Lý and Hóa Học
for subj in ["vật lý 2025", "hóa học 2025"]:
    print(f"=== Searching for {subj} ===")
    results = search_subject(subj)
    for title, href in results[:5]:
        print(f"Title: {title}")
        print(f"Page: {href}")
        pdf_link = get_pdf_download_link(href)
        print(f"PDF Link: {pdf_link}")
        print("-" * 50)
