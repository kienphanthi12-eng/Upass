"""
reimport_ly_hoa.py — Re-import LY Ca Mau (203) + HOA Lam Dong (204) + HOA Da Nang (206)
with fixed parser that handles:
  - plain 2-row answer tables [1,2,...] / [A,B,...] (LY Ca Mau)
  - composite DS key tables [1a,1b,1c,1d,...] / [S,Đ,...] (LY Ca Mau)
  - false-stop fix: 'đáp án của mình' no longer kills PHẦN III parsing (HOA Da Nang)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import db
from import_exam_docx import run_docx_pipeline
from import_subjects_pipeline import get_used_cities, assign_city, set_city

DATA_DIR = Path("data/pdfs")

# Exams to delete
# 203 = LY Ca Mau  (Toronto — all 27 no_answer, plain answer table format unsupported)
# 204 = HOA Lam Dong (Philadelphia — 24 no_answer, (Câu,Đáp án)×n table now working)
# 206 = HOA Da Nang  (Boston — only 18q imported, false-stop killed PHẦN III)
BAD_EXAM_IDS = [203, 204, 206]

TO_IMPORT = [
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tn-THPT-nam-2026-Vat-Li-So-GD-Ca-Mau-Lan-1.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_Vat_Li_2026_So_Gd_Ca_Mau_Lan_1',
        'subject_id': 2,
        'label': 'LY Ca Mau',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Hoa-So-GD-Lam-Dong-.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Mon_Hoa_So_Gd_Lam_Dong',
        'subject_id': 3,
        'label': 'HOA Lam Dong',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-TN-THPT-nam-2026-mon-HOA-So-GD-Da-Nang-lan-1.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Mon_Hoa_So_Gd_Da_Nang_Lan_1',
        'subject_id': 3,
        'label': 'HOA Da Nang',
    },
]


def cascade_delete(exam_id: int, conn):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM student_answers WHERE question_id IN "
            "(SELECT id FROM questions WHERE exam_id=%s)", (exam_id,))
        cur.execute(
            "DELETE FROM question_reports WHERE question_id IN "
            "(SELECT id FROM questions WHERE exam_id=%s)", (exam_id,))
        cur.execute(
            "DELETE FROM question_usage WHERE question_id IN "
            "(SELECT id FROM questions WHERE exam_id=%s) OR exam_id=%s",
            (exam_id, exam_id))
        cur.execute("DELETE FROM exam_submissions WHERE exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM assignments WHERE exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM draft_exams WHERE published_exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM questions WHERE exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM exams WHERE id=%s", (exam_id,))


def main():
    db.init_pool()

    print("=== Step 1: Xoa exams bi loi ===")
    with db.get_conn() as conn:
        for eid in BAD_EXAM_IDS:
            cascade_delete(eid, conn)
            print(f"  Deleted exam {eid}")
        conn.commit()
    print("  Done.")

    print("\n=== Step 2: Re-import DOCX direct ===")
    results = []
    for item in TO_IMPORT:
        docx_path = DATA_DIR / item['docx']
        if not docx_path.exists():
            print(f"  ERROR: DOCX not found: {docx_path}")
            results.append({'label': item['label'], 'ok': False, 'reason': 'DOCX not found'})
            continue

        print(f"\n[{item['label']}] {item['docx'][:70]}")
        t = time.time()
        try:
            exam_id = run_docx_pipeline(
                docx_path=str(docx_path),
                title=item['title'],
                year=2026,
                subject_id=item['subject_id'],
            )
            elapsed = time.time() - t
            used_cities = get_used_cities()
            city = assign_city(used_cities)
            set_city(exam_id, city)
            print(f"  exam_id={exam_id} | city={city} | took {elapsed:.1f}s")
            results.append({'label': item['label'], 'ok': True, 'exam_id': exam_id, 'city': city})
        except Exception as e:
            import traceback
            traceback.print_exc()
            results.append({'label': item['label'], 'ok': False, 'reason': str(e)})

    print("\n=== Summary ===")
    for r in results:
        status = "OK" if r['ok'] else f"FAIL: {r.get('reason','?')}"
        city  = r.get('city', '-')
        eid   = r.get('exam_id', '-')
        print(f"  {r['label']:20} | {status:8} | exam_id={eid} | city={city}")


if __name__ == '__main__':
    main()
