import sys
import io
import asyncio
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from database import db
from import_subjects_pipeline import process_exam

ENGLISH_URLS = [
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-thpt-tay-ninh-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-vinh-long-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-gia-lai-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-lam-dong-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-ha-tinh-lan-2-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-nghe-an-lan-3-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-hai-phong-lan-2-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-bac-ninh-lan-2-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-can-tho-giai-chi-tiet/',
    'https://thuvienhoclieu.com/de-thi-thu-tot-nghiep-tieng-anh-2026-so-gd-an-giang-giai-chi-tiet/'
]

async def main():
    print("=== Starting Batch Import of 10 English Exams ===")
    db.init_pool()
    
    results = []
    t_start_all = time.time()
    
    for idx, url in enumerate(ENGLISH_URLS, 1):
        print(f"\n[{idx}/10] Processing: {url}")
        t_start = time.time()
        try:
            success = await process_exam(url, "ANH")
            elapsed = time.time() - t_start
            status = "SUCCESS" if success else "FAILED"
            print(f"[{idx}/10] Status: {status} (took {elapsed:.1f}s)")
            results.append((url, status, elapsed))
        except Exception as e:
            elapsed = time.time() - t_start
            print(f"[{idx}/10] Status: EXCEPTION ({e}) (took {elapsed:.1f}s)")
            results.append((url, "EXCEPTION", elapsed))
        
        # Sleep to avoid rate limiting
        time.sleep(2)
        
    print("\n=== Final Batch Report ===")
    total_elapsed = time.time() - t_start_all
    for idx, (url, status, elapsed) in enumerate(results, 1):
        print(f"  {idx:02d}. {url} -> {status} ({elapsed:.1f}s)")
    print(f"\nTotal time: {total_elapsed:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
