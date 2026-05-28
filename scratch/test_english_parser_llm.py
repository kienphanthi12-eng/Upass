import sys
import io
import asyncio
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from import_exam_deepseek import (
    normalize_raw_markdown,
    split_normalized_text,
    process_single_question,
    _merge_parser_answers
)

async def test_parse():
    folder = Path("C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-So-GD-An-Giang.pdf-beb0786d-163d-4ee3-8e65-373f9cca1867")
    md_path = folder / "full.md"
    raw_md = md_path.read_text(encoding="utf-8")
    
    print("Step 1: Normalizing raw markdown using DeepSeek V3...")
    normalized_md = await normalize_raw_markdown(raw_md)
    print(f"Normalized markdown size: {len(normalized_md)} chars")
    
    # Save normalized markdown to scratch for inspection
    Path("scratch/normalized_an_giang.md").write_text(normalized_md, encoding="utf-8")
    
    print("\nStep 2: Splitting normalized text into questions...")
    questions = split_normalized_text(normalized_md)
    print(f"Found {len(questions)} questions.")
    
    for q in questions[:5]:
        print(f"  Q{q['question_index']} raw_content preview: {q['raw_content'][:150]}...")
        
    print("\nStep 3: Extracting question JSON for the first 5 questions...")
    import aiohttp
    semaphore = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as session:
        tasks = [process_single_question(q, folder, semaphore, session) for q in questions[:5]]
        results = await asyncio.gather(*tasks)
        
    for r in results:
        if r:
            print(f"  Q{r['question_index']}: Text={r['question_text'][:80]} | Correct={r['correct_answer']} | Options={r['options']}")
        else:
            print("  Failed to extract JSON.")

if __name__ == "__main__":
    asyncio.run(test_parse())
