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
    docx_url = "https://thuvienhoclieu.com/wp-content/uploads/2026/05/thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-THPT-Tay-Ninh.docx"
    pdf_dir = Path("data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    docx_path = pdf_dir / "thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-THPT-Tay-Ninh.docx"
    pdf_path = docx_path.with_suffix(".pdf")
    
    print("1. Downloading DOCX...")
    if not docx_path.exists():
        ok = download_file(docx_url, docx_path)
        if not ok:
            print("Download failed.")
            return
    else:
        print("DOCX already exists.")
        
    print("\n2. Converting DOCX to PDF...")
    if not pdf_path.exists():
        ok = convert_docx_to_pdf(docx_path, pdf_path)
        if not ok:
            print("Conversion failed.")
            return
    else:
        print("PDF already exists.")
        
    print("\n3. Running MinerU OCR...")
    mineru_folder = call_mineru_api(pdf_path)
    if not mineru_folder:
        print("OCR failed.")
        return
        
    print(f"\n4. Parsing OCR markdown from {mineru_folder}...")
    md_path = mineru_folder / "full.md"
    raw_md = md_path.read_text(encoding="utf-8")
    
    parsed_exams = parse_exam_file(raw_md)
    if not parsed_exams:
        print("No exams parsed.")
        return
        
    exam = parsed_exams[0]
    print(f"Success! Parsed exam: {exam.subject} | Ma de: {exam.ma_de}")
    print(f"Total questions parsed: {len(exam.questions)}")
    for q in exam.questions[:10]:
        print(f"  Q{q.index} ({q.q_type}): Answer={q.correct_answer} | Text={q.question_text[:80]}...")
        if q.options:
            print(f"    Options: {list(q.options.keys())}")
            
if __name__ == "__main__":
    asyncio.run(main())
