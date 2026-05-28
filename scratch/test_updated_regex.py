import sys
import io
import re
from pathlib import Path

# Add absolute project directory to path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))
print(f"Project directory added to path: {project_dir}")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Updated patterns
_CAU_PAT = re.compile(
    r"(?:"
    r"(?:^|\n)\s*(?:[Cc][aâ][uư]?|CAU|C[ÂA]U|[Qq]uestion|[Qq]uest|QUESTION|QUEST)\s*\.?\s*(\d+)\s*[.:\-–]?\s*"
    r"|"
    r"\b(?:[Cc][aâ][uư]?|CAU|C[ÂA]U|[Qq]uestion|[Qq]uest|QUESTION|QUEST)\s*\.?\s*(\d+)\s*[.:\-–]\s*"
    r")"
    r"(?=\D|$)",
    re.MULTILINE,
)

_CAU_PREFIX = re.compile(
    r"^(?:[Cc][aâ][uư]?|[Qq]uestion|[Qq]uest)\s*\d+\s*[.:\-–]?\s*",
    re.IGNORECASE | re.MULTILINE,
)

def main():
    folder = Path("C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-THPT-Tay-Ninh.pdf-da5de753-7c83-4b01-afd6-a26bee09a553")
    md_path = folder / "full.md"
    raw_md = md_path.read_text(encoding="utf-8")
    
    # Check split_document from smart_parser (but let's do a basic check here)
    from processor.smart_parser import split_document, detect_sections
    exam_body, answer_block, solution_raw = split_document(raw_md)
    print(f"Exam body length: {len(exam_body)}")
    print(f"Answer block length: {len(answer_block)}")
    print(f"Solution raw length: {len(solution_raw)}")
    
    # Question detection
    matches = list(_CAU_PAT.finditer(exam_body))
    print(f"Total _CAU_PAT matches in exam_body: {len(matches)}")
    
    questions = []
    for i, m in enumerate(matches):
        q_num = int(m.group(1) or m.group(2))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(exam_body)
        raw = exam_body[start:end].strip()
        questions.append((q_num, raw))
        
    print(f"Detected questions count: {len(questions)}")
    detected_nums = sorted([q_num for q_num, _ in questions])
    print(f"Detected question numbers: {detected_nums}")
    all_expected = set(range(1, 41))
    missing = all_expected - set(detected_nums)
    print(f"Missing question numbers: {sorted(list(missing))}")
    for q_num, raw in questions[:5]:
        print(f"  Q{q_num}: {raw[:80]}...")

        
    # Debug: Search for number 32 in the first 25000 characters
    print("\n=== Searching for number '32' in exam_body ===")
    for m in re.finditer(r"\b32\b", raw_md[:25000]):
        start = max(0, m.start() - 50)
        end = min(len(raw_md), m.end() + 50)
        print(f"Match found at position {m.start()}:\n{raw_md[start:end]!r}\n" + "-"*40)



if __name__ == "__main__":
    main()
