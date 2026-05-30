import requests

urls = [
    "https://hcm.edu.vn/uploads/thptnguyenhien/news/2024_11/2-de-minh-hoa-gioi-thieu-2025-final-0311-241112070045.pdf",
    "https://hcm.edu.vn/uploads/thptnguyenhien/news/2024_12/2-de-minh-hoa-gioi-thieu-2025-final-0311-241112070045.pdf",
    "https://hcm.edu.vn/uploads/thptnguyenhien/news/2025_03/2-de-minh-hoa-gioi-thieu-2025-final-0311-241112070045.pdf",
    "https://www.hcm.edu.vn/uploads/thptnguyenhien/news/2024_11/2-de-minh-hoa-gioi-thieu-2025-final-0311-241112070045.pdf",
    "https://www.hcm.edu.vn/uploads/thptnguyenhien/news/2025_3/2-de-minh-hoa-gioi-thieu-2025-final-0311-241112070045.pdf"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

for url in urls:
    try:
        r = requests.head(url, headers=headers, timeout=10)
        print(f"URL: {url} -> Status: {r.status_code}")
        if r.status_code == 200:
            print("  FOUND!")
    except Exception as e:
        print(f"Error {url}: {e}")
