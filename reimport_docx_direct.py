"""
reimport_docx_direct.py — Xóa 8 exam LY/HOA/SU bị mất dấu tiếng Việt (MinerU với language=ch),
re-import bằng DOCX direct pipeline (giữ dấu đúng).
"""
import sys
import io
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import db
from import_exam_docx import run_docx_pipeline, auto_hide_buggy
from import_subjects_pipeline import get_used_cities, assign_city, set_city

DATA_DIR = Path("data/pdfs")

# Exams bị lỗi cần xóa (MinerU OCR mất dấu tiếng Việt)
BAD_EXAM_IDS = [194, 195, 196, 197, 198, 199, 200, 201]

# DOCX files + titles (dùng format underscore để thống nhất)
TO_IMPORT = [
    # Vật Lý
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-TN-THPT-2026-mon-VAT-LI-GD-DONG-NAI.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_Vat_Li_2026_So_Gd_Dong_Nai_Lan_1',
        'subject_id': 2,
        'label': 'LY Dong Nai',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tn-THPT-nam-2026-Vat-Li-So-GD-Ca-Mau-Lan-1.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_Vat_Li_2026_So_Gd_Ca_Mau_Lan_1',
        'subject_id': 2,
        'label': 'LY Ca Mau',
    },
    # Hóa Học
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Hoa-So-GD-Lam-Dong-.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Mon_Hoa_So_Gd_Lam_Dong',
        'subject_id': 3,
        'label': 'HOA Lam Dong',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-TN-2026-mon-Hoa-So-GD-Phu-Tho-Lan-2.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Mon_Hoa_So_Gd_Phu_Tho_Lan_2',
        'subject_id': 3,
        'label': 'HOA Phu Tho',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-TN-THPT-nam-2026-mon-HOA-So-GD-Da-Nang-lan-1.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Mon_Hoa_So_Gd_Da_Nang_Lan_1',
        'subject_id': 3,
        'label': 'HOA Da Nang',
    },
    # Lịch Sử
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Lich-Su-So-GD-Lam-Dong.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Lich_Su_So_Gd_Lam_Dong',
        'subject_id': 6,
        'label': 'SU Lam Dong',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-TN-THPT-2026-Mon-Lich-Su-So-GD-PHU-THO-lan-1.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_Thpt_2026_Lich_Su_So_Gd_Phu_Tho',
        'subject_id': 6,
        'label': 'SU Phu Tho',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-nam-2026-Lich-su-So-GD-Da-Nang-Lan-1.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Lich_Su_So_Gd_Da_Nang_Lan_1',
        'subject_id': 6,
        'label': 'SU Da Nang',
    },
]


def cascade_delete(exam_id: int, conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM student_answers WHERE question_id IN (SELECT id FROM questions WHERE exam_id=%s)", (exam_id,))
        cur.execute("DELETE FROM question_reports WHERE question_id IN (SELECT id FROM questions WHERE exam_id=%s)", (exam_id,))
        cur.execute("DELETE FROM question_usage WHERE question_id IN (SELECT id FROM questions WHERE exam_id=%s) OR exam_id=%s", (exam_id, exam_id))
        cur.execute("DELETE FROM exam_submissions WHERE exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM assignments WHERE exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM draft_exams WHERE published_exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM questions WHERE exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM exams WHERE id=%s", (exam_id,))


def main():
    db.init_pool()

    # Step 1: Xóa 8 exam bị lỗi
    print("=== Step 1: Xoa 8 exam bi mat dau ===")
    with db.get_conn() as conn:
        for eid in BAD_EXAM_IDS:
            cascade_delete(eid, conn)
            print(f"  Deleted exam {eid}")
        conn.commit()
    print("  Done.")

    # Step 2: Re-import bằng DOCX direct
    print("\n=== Step 2: Re-import DOCX direct ===")
    results = []
    for item in TO_IMPORT:
        docx_path = DATA_DIR / item['docx']
        if not docx_path.exists():
            print(f"  ERROR: DOCX not found: {docx_path}")
            results.append({'label': item['label'], 'ok': False, 'reason': 'DOCX not found'})
            continue

        print(f"\n[{item['label']}] {item['docx'][:60]}")
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
            print(f"  ERROR: {e}")
            results.append({'label': item['label'], 'ok': False, 'reason': str(e)})

    # Summary
    print("\n=== Summary ===")
    for r in results:
        status = "OK" if r['ok'] else f"FAIL: {r.get('reason','?')}"
        city = r.get('city', '-')
        eid = r.get('exam_id', '-')
        print(f"  {r['label']:20} | {status:6} | exam_id={eid} | city={city}")


if __name__ == '__main__':
    main()
