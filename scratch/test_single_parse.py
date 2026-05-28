import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from processor.smart_parser import split_document, detect_sections, detect_questions, parse_exam_file

def main():
    folder = Path("C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Vat-Li-So-GD-Lam-Dong-.pdf-406acd9e-0fbe-4aa4-adc3-af839963a842")
    md_path = folder / "full.md"
    raw_md = md_path.read_text(encoding="utf-8")
    
    exam_body, answer_block, solution_raw = split_document(raw_md)
    print("=== Document Split ===")
    print(f"Exam body length: {len(exam_body)}")
    print(f"Answer block length: {len(answer_block)}")
    print(f"Solution raw length: {len(solution_raw)}")
    
    print("\n=== Section Detection ===")
    sections = detect_sections(exam_body)
    for sec_num, sec_text in sorted(sections.items()):
        print(f"Section {sec_num}: length={len(sec_text)}")
        print(f"First 100 chars: {sec_text[:100]!r}")
        
        # Detect questions in this section
        qs = detect_questions(sec_text, sec_num)
        print(f"  -> Found {len(qs)} questions: {[q['index'] for q in qs]}")

    print("\n=== Full Parse ===")
    exams = parse_exam_file(raw_md)
    if exams:
        exam = exams[0]
        print(f"Total parsed questions: {len(exam.questions)}")
        for q in exam.questions:
            print(f"  Q{q.index} P{q.section} ({q.q_type}): Answer={q.correct_answer} | Expl={q.explanation is not None}")
    else:
        print("No exams parsed.")

if __name__ == "__main__":
    main()
