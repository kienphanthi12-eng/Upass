import requests

urls = [
    "https://thptvinhbao.haiphong.edu.vn/tin-tuc-su-kien/tin-tuc-chung/de-minh-hoa-thi-danh-gia-nang-luc-2025-cua-dh-quoc-gia-tp-hcm.html",
    "https://thpt-vinhbao.haiphong.edu.vn/tin-tuc-su-kien/tin-tuc-chung/de-minh-hoa-thi-danh-gia-nang-luc-2025-cua-dh-quoc-gia-tp-hcm.html",
    "https://c3vinhbao.haiphong.edu.vn/tin-tuc-su-kien/tin-tuc-chung/de-minh-hoa-thi-danh-gia-nang-luc-2025-cua-dh-quoc-gia-tp-hcm.html",
    "http://thptvinhbao.haiphong.edu.vn/tin-tuc-su-kien/tin-tuc-chung/de-minh-hoa-thi-danh-gia-nang-luc-2025-cua-dh-quoc-gia-tp-hcm.html",
    "http://thpt-vinhbao.haiphong.edu.vn/tin-tuc-su-kien/tin-tuc-chung/de-minh-hoa-thi-danh-gia-nang-luc-2025-cua-dh-quoc-gia-tp-hcm.html"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

for url in urls:
    try:
        r = requests.head(url, headers=headers, timeout=5)
        print(f"URL: {url} -> Status: {r.status_code}")
    except Exception as e:
        print(f"Error {url}: {e}")
