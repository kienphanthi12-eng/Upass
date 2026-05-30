import requests

urls = [
    "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQECPJW530YHbSLxXmz5UqGaGA5V1aEAfQJlYLKq1yV6YhHGC4DkvZjLxLVQoKgyz4Kjpbatw261KgfANJgwJ0yhIhnZhrVDPk1-orMTw5kkqAt_gv_NGp1eQMCnfsg0dRVY1lH1I16yYqLF3STnJ56cXf77cnw0wHDGM4DnBfMf"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

for i, url in enumerate(urls, 1):
    try:
        r = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        print(f"URL {i} final destination: {r.url}")
    except Exception as e:
        print(f"Error resolving URL {i}: {e}")
