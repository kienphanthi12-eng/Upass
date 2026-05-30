"""
reimport_su_anh.py — Xóa SU 207/208 (thiếu đáp án) và ANH 184/185/193 (LLM/OCR lỗi),
re-import bằng DOCX direct pipeline với parser đã sửa.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import db
from import_exam_docx import run_docx_pipeline
from import_subjects_pipeline import get_used_cities, assign_city, set_city

DATA_DIR = Path("data/pdfs")

# ─── Exams cần xóa ─────────────────────────────────────────────────────────────
# 207 = SU Lam Dong (Miami  — 24 no_answer)
# 208 = SU Phu Tho  (Atlanta — 28 no_answer)
# 184 = ANH Vancouver (LLM pipeline, 22 no_answer)
# 185 = ANH Montreal  (LLM pipeline,  8 no_answer)
# 193 = ANH Marseille (MinerU, 2 no_answer)
BAD_EXAM_IDS = [207, 208, 184, 185, 193]

# ─── DOCX files để re-import ──────────────────────────────────────────────────
TO_IMPORT = [
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
    # Tiếng Anh
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-So-GD-Lam-Dong-.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Tieng_Anh_So_Gd_Lam_Dong',
        'subject_id': 9,
        'label': 'ANH Lam Dong',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-So-GD-An-Giang.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Tieng_Anh_So_Gd_An_Giang',
        'subject_id': 9,
        'label': 'ANH An Giang',
    },
    {
        'docx': 'thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Tieng-Anh-So-GD-Gia-Lai.docx',
        'title': '2026_De_Thi_Thu_Tot_Nghiep_2026_Tieng_Anh_So_Gd_Gia_Lai',
        'subject_id': 9,
        'label': 'ANH Gia Lai',
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

    # Step 1: Xóa exams lỗi
    print("=== Step 1: Xoa exams bi loi ===")
    with db.get_conn() as conn:
        for eid in BAD_EXAM_IDS:
            cascade_delete(eid, conn)
            print(f"  Deleted exam {eid}")
        conn.commit()
    print("  Done.")

    # Step 2: Re-import bằng DOCX direct với parser đã sửa
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

    # Summary
    print("\n=== Summary ===")
    for r in results:
        status = "OK" if r['ok'] else f"FAIL: {r.get('reason','?')}"
        city  = r.get('city', '-')
        eid   = r.get('exam_id', '-')
        print(f"  {r['label']:20} | {status:8} | exam_id={eid} | city={city}")


if __name__ == '__main__':
    main()
