# DEPRECATED — script thử nghiệm dùng pipeline DeepSeek cũ (normalize_raw_markdown,
# split_normalized_text, process_single_question). Các hàm này đã bị xóa khỏi
# import_exam_deepseek.py (refactor 2026-06-01). Script này không còn chạy được.
import sys
import io
import asyncio
import time
import aiohttp
from pathlib import Path

# Fix terminal encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from database import db
from import_exam_deepseek import (
    normalize_raw_markdown,
    split_normalized_text,
    process_single_question,
    _merge_parser_answers,
    insert_to_supabase,
    _create_exam_record
)
from import_subjects_pipeline import (
    get_used_cities,
    assign_city,
    set_city,
    build_exam_title,
    scrape_docx_url,
    find_existing_mineru_folder
)
import config

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

SEMAPHORE = asyncio.Semaphore(5)

def delete_existing_exam(title: str):
    """Deletes an exam and all its questions and associated tables cascadingly."""
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            # Get exam_id
            cur.execute("SELECT id FROM exams WHERE title = %s", (title,))
            row = cur.fetchone()
            if row:
                exam_id = row[0]
                print(f"  Deleting existing exam title={title} (id={exam_id}) cascadingly...")
                
                # 1. delete student_answers referencing questions of this exam
                cur.execute("DELETE FROM student_answers WHERE question_id IN (SELECT id FROM questions WHERE exam_id = %s)", (exam_id,))
                # 2. delete question_reports referencing questions of this exam
                cur.execute("DELETE FROM question_reports WHERE question_id IN (SELECT id FROM questions WHERE exam_id = %s)", (exam_id,))
                # 3. delete question_usage referencing questions or exam
                cur.execute("DELETE FROM question_usage WHERE question_id IN (SELECT id FROM questions WHERE exam_id = %s) OR exam_id = %s", (exam_id, exam_id))
                # 4. delete exam_submissions
                cur.execute("DELETE FROM exam_submissions WHERE exam_id = %s", (exam_id,))
                # 5. delete assignments
                cur.execute("DELETE FROM assignments WHERE exam_id = %s", (exam_id,))
                # 6. delete draft_exams
                cur.execute("DELETE FROM draft_exams WHERE published_exam_id = %s", (exam_id,))
                # 7. delete questions
                cur.execute("DELETE FROM questions WHERE exam_id = %s", (exam_id,))
                # 8. delete exam
                cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))
                
                conn.commit()
                print("  Deleted successfully.")


async def import_exam_llm(page_url: str, subject_id: int):
    # 1. Scrape DOCX URL and build title
    docx_url = scrape_docx_url(page_url)
    if not docx_url:
        print(f"Error: Could not scrape DOCX URL from {page_url}")
        return False
        
    title = build_exam_title(page_url, "Tiếng Anh")
    print(f"\n==================================================")
    print(f"Running LLM Pipeline for: {title}")
    print(f"Page URL: {page_url}")
    print(f"==================================================")

    # Clean up existing exam record first to ensure clean import
    delete_existing_exam(title)

    # 2. Locate existing MinerU OCR folder
    docx_name = docx_url.split("/")[-1]
    pdf_name = docx_name.replace(".docx", ".pdf")
    exam_folder = find_existing_mineru_folder(pdf_name)
    if not exam_folder:
        print(f"Error: Could not find MinerU OCR folder for {pdf_name}")
        return False
    
    print(f"Found MinerU OCR folder: {exam_folder.name}")

    # 3. Read raw markdown
    md_path = exam_folder / "full.md"
    if not md_path.exists():
        print(f"Error: {md_path} does not exist.")
        return False
    raw_md = md_path.read_text(encoding="utf-8")
    print(f"Raw markdown: {len(raw_md)} chars")

    # 4. Normalize raw markdown using DeepSeek V3
    print("Step 1: Normalizing raw markdown using DeepSeek V3...")
    normalized_md = await normalize_raw_markdown(raw_md)
    # Save normalized markdown for debugging/audit
    (exam_folder / "normalized.md").write_text(normalized_md, encoding="utf-8")
    print(f"Normalized markdown: {len(normalized_md)} chars")

    # 5. Split normalized text into questions
    print("Step 2: Splitting normalized text into questions...")
    questions = split_normalized_text(normalized_md)
    print(f"Found {len(questions)} questions in normalized text.")

    if not questions:
        print("Error: No questions found after split.")
        return False

    # 6. Extract details for each question using DeepSeek V3 (parallel with semaphore)
    print("Step 3: Extracting question JSON via DeepSeek V3...")
    async with aiohttp.ClientSession() as http_session:
        tasks = []
        for q in questions:
            tasks.append(process_single_question(q, exam_folder, SEMAPHORE, http_session))
        
        raw_results = await asyncio.gather(*tasks)
        valid_results = [r for r in raw_results if r is not None]
    
    print(f"Extracted {len(valid_results)}/{len(questions)} valid question JSONs.")

    if not valid_results:
        print("Error: No valid question JSONs extracted.")
        return False

    # 7. Merge answers from answer table
    print("Step 4: Merging answers from answer table...")
    merged_results = _merge_parser_answers(valid_results, raw_md)
    print(f"Final merged questions count: {len(merged_results)}")

    # 8. Create exam record in DB
    print("Step 5: Creating exam record in DB...")
    exam_id = _create_exam_record(title, 2026, subject_id)
    print(f"Created exam in DB with ID: {exam_id}")

    # 9. Insert questions to Supabase
    print("Step 6: Inserting questions to Supabase...")
    ok_count = 0
    err_count = 0
    for q_data in merged_results:
        success = insert_to_supabase(q_data, exam_id, subject_id)
        if success:
            ok_count += 1
        else:
            err_count += 1
    
    print(f"Successfully inserted {ok_count} questions. Errors: {err_count}")

    # 10. Assign unique display title (city)
    used_cities = get_used_cities()
    city = assign_city(used_cities)
    set_city(exam_id, city)
    print(f"Assigned display_title (city): {city} to exam_id={exam_id}")
    
    return ok_count == 40

async def main():
    print("=== Starting LLM Batch Import of 10 English Exams ===")
    db.init_pool()
    subject_id = 9 # ANH
    
    results = []
    t_start_all = time.time()
    
    for idx, url in enumerate(ENGLISH_URLS, 1):
        print(f"\n[{idx}/10] LLM Processing: {url}")
        t_start = time.time()
        try:
            success = await import_exam_llm(url, subject_id)
            elapsed = time.time() - t_start
            status = "SUCCESS" if success else "FAILED"
            print(f"[{idx}/10] Status: {status} (took {elapsed:.1f}s)")
            results.append((url, status, elapsed))
            if not success:
                print(f"[CRITICAL] Stop immediately: {url} failed to import exactly 40 questions.")
                sys.exit(1)
        except Exception as e:
            elapsed = time.time() - t_start
            print(f"[{idx}/10] Status: EXCEPTION ({e}) (took {elapsed:.1f}s)")
            results.append((url, "EXCEPTION", elapsed))
            print(f"[CRITICAL] Stop immediately due to exception: {e}")
            sys.exit(1)
        
        # Sleep to avoid rate limiting
        await asyncio.sleep(2)
        
    print("\n=== Final LLM Batch Report ===")
    total_elapsed = time.time() - t_start_all
    for idx, (url, status, elapsed) in enumerate(results, 1):
        print(f"  {idx:02d}. {url} -> {status} ({elapsed:.1f}s)")
    print(f"\nTotal time: {total_elapsed:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
