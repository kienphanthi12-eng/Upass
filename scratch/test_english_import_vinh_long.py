import sys
import io
import asyncio
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from import_subjects_pipeline import download_file, convert_docx_to_pdf, call_mineru_api
from processor.smart_parser import parse_exam_file

async def main():
    docx_url = "https://thuvienhoclieu.com/wp-content/uploads/2026/05/thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-So-GD-Vinh-Long.docx"
    pdf_dir = Path("data/pdfs")
    docx_path = pdf_dir / "thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-So-GD-Vinh-Long.docx"
    pdf_path = docx_path.with_suffix(".pdf")
    
    print("1. Downloading DOCX...")
    if not docx_path.exists():
        ok = download_file(docx_url, docx_path)
        if not ok:
            print("Download failed.")
            return
            
    print("\n2. Converting DOCX to PDF...")
    if not pdf_path.exists():
        ok = convert_docx_to_pdf(docx_path, pdf_path)
        if not ok:
            print("Conversion failed.")
            return
            
    print("\n3. Running MinerU OCR...")
    mineru_folder = call_mineru_api(pdf_path)
    if not mineru_folder:
        print("OCR failed.")
        return
        
    print("\n4. Parsing OCR markdown using full parse_exam_file...")
    md_path = mineru_folder / "full.md"
    raw_md = md_path.read_text(encoding="utf-8")
    exams = parse_exam_file(raw_md)
    if exams:
        exam = exams[0]
        print(f"Total parsed questions: {len(exam.questions)}")
        for q in exam.questions[:10]:
            print(f"  Q{q.index} ({q.q_type}): Answer={q.correct_answer} | Text={q.question_text[:80]}...")
    else:
        print("No exams parsed.")


if __name__ == "__main__":
    asyncio.run(main())
