"""
processor/azota_job.py — Background job: parse đề Azota (docx/pdf) → draft_exams/draft_questions.

Spawn bởi web upload route (Node spawn python) khi giáo viên chọn import_type='azota'.
Chạy LOCAL (cần Python + PIL/PyMuPDF; Vercel không chạy được — giống crop_pdf_job.py).

Args:
  --file_path  đường dẫn file tạm (.docx/.pdf)
  --job_id     UUID ocr_jobs
  --user_id    UUID giáo viên
  --filename   tên file gốc
  --subject    mã môn (TOAN/LY/HOA/...)
  --kind       docx | pdf
  --no-llm     (tùy chọn) tắt DeepSeek, dùng regex/keyword
"""
import os
import sys
import io
import re
import json
import argparse
import shutil
import tempfile
from pathlib import Path

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
# Ưu tiên cấu hình trong root .env để đồng nhất với chạy CLI (có các key của Python/OpenAI hoạt động)
load_dotenv(override=True)
# Nạp thêm .env.local nhưng không override các biến quan trọng đã có
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", ".env.local"), override=False)

from database import db
from processor import subject_structures as ss
from processor import azota_llm
from processor.azota_merge import merge_answers

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL",
                         f"https://{os.getenv('SUPABASE_PROJECT_ID', 'zabvdgnucfanvbjjgnic')}.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET = "exam-images"


# ─────────────────────────────────────────────────────────────────────────────
# Upload ảnh
# ─────────────────────────────────────────────────────────────────────────────

def _upload_image(abspath: str, user_id: str, job_id: str) -> str:
    name = Path(abspath).name
    storage_path = f"{user_id}/{job_id}/{name}"
    if SUPABASE_SERVICE_KEY and SUPABASE_SERVICE_KEY != "your_service_role_key_here":
        url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}"
        headers = {"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}", "Content-Type": "image/png"}
        try:
            with open(abspath, "rb") as f:
                data = f.read()
            r = requests.post(url, data=data, headers=headers)
            if r.status_code not in (200, 201):
                r = requests.put(url, data=data, headers=headers)
            if r.status_code in (200, 201):
                return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{storage_path}"
        except Exception as e:
            print(f"Supabase upload lỗi: {e}, fallback local")
    # Fallback local web/public
    root = Path(__file__).parent.parent
    dest_dir = root / "web" / "public" / "exam-images" / user_id / job_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(abspath, dest_dir / name)
    return f"/exam-images/{user_id}/{job_id}/{name}"


def _publish_images(q, user_id: str, job_id: str) -> None:
    for abspath in q.image_paths:
        url = _upload_image(abspath, user_id, job_id)
        old, new = f"]({abspath})", f"]({url})"
        q.question_text = q.question_text.replace(old, new)
        if q.options:
            q.options = {k: v.replace(old, new) for k, v in q.options.items()}
        if q.explanation:
            q.explanation = q.explanation.replace(old, new)


# ─────────────────────────────────────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────────────────────────────────────

def _set_job_error(job_id: str, msg: str) -> None:
    try:
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE ocr_jobs SET status='error', error_msg=%s, updated_at=NOW() WHERE id=%s",
                            (msg[:500], job_id))
    except Exception as e:
        print(f"Không cập nhật được job error: {e}")


def _detect_exam_type(title: str) -> str:
    t = title.lower()
    if "ôn" in t or "on thi" in t:
        return "on_thi"
    if "khảo sát" in t or "khao sat" in t:
        return "KS"
    return "thi_thu"


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file_path", required=True)
    ap.add_argument("--job_id", required=True)
    ap.add_argument("--user_id", required=True)
    ap.add_argument("--filename", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--kind", choices=["docx", "pdf"], required=True)
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()

    use_llm = not args.no_llm
    code = args.subject.upper()
    file_path = Path(args.file_path)
    title = re.sub(r"[-_]+", " ", args.filename.rsplit(".", 1)[0]).strip()[:200]
    img_dir = tempfile.mkdtemp()

    try:
        db.init_pool()
        subject_id = db.get_subject_id(code) or 1

        # ── Parse ───────────────────────────────────────────────────────────
        if args.kind == "docx":
            from processor.azota_parser import parse_azota_docx, is_azota_format
            ok_fmt, diag = is_azota_format(str(file_path))
            if not ok_fmt:
                _set_job_error(args.job_id,
                               f"File .docx không đúng format Azota ({diag}). "
                               f"Vui lòng tải lại dạng PDF để dùng OCR (MinerU).")
                return
            exam = parse_azota_docx(str(file_path), image_dir=img_dir)
        else:
            from processor.azota_pdf_parser import parse_azota_pdf
            exam = parse_azota_pdf(str(file_path))

        if not exam.questions:
            _set_job_error(args.job_id, "Không trích được câu hỏi nào từ file.")
            return

        # ── Đáp án + merge + validate + enrich ──────────────────────────────
        table_answers = azota_llm.extract_answers(exam.raw_answer_block, exam.ma_de, use_llm=use_llm)
        merge_answers(exam, table_answers)
        warnings = ss.validate(exam, code)
        azota_llm.enrich_topics_levels(exam.questions, code, use_llm=use_llm)

        # ── Insert draft ────────────────────────────────────────────────────
        review_count = 0
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO draft_exams (teacher_id, ocr_job_id, title, exam_type, subject_id, status)
                       VALUES (%s, %s, %s, %s, %s, 'draft') RETURNING id""",
                    (args.user_id, args.job_id, title, _detect_exam_type(title), subject_id),
                )
                draft_id = cur.fetchone()[0]

                for q in exam.questions:
                    _publish_images(q, args.user_id, args.job_id)
                    qnum = q.index + (q.section - 1) * 100
                    options = q.options if q.options else None
                    if q.needs_review:
                        review_count += 1
                    cur.execute(
                        """INSERT INTO draft_questions
                           (draft_exam_id, question_number, question_type, content, options,
                            correct_answer, difficulty_level, explanation, needs_review, review_reason)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (draft_id, qnum, q.q_type, q.question_text,
                         json.dumps(options, ensure_ascii=False) if options else None,
                         q.correct_answer, q.level or "Thông hiểu", q.explanation,
                         q.needs_review, q.review_reason or None),
                    )

                note = f"{len(exam.questions)} câu"
                if review_count:
                    note += f", {review_count} câu cần review"
                if warnings:
                    note += f"; cảnh báo cấu trúc: {' | '.join(warnings)[:300]}"
                cur.execute(
                    "UPDATE ocr_jobs SET status='done', question_count=%s, updated_at=NOW() WHERE id=%s",
                    (len(exam.questions), args.job_id),
                )

        print(f"Azota job {args.job_id} OK → draft {draft_id} ({note})")

    except Exception as e:
        import traceback
        traceback.print_exc()
        _set_job_error(args.job_id, str(e))
    finally:
        shutil.rmtree(img_dir, ignore_errors=True)
        try:
            os.unlink(file_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
