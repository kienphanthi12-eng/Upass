"""
import_azota.py — CLI import đề soạn theo format Azota → DB production (exams/questions).

Router:
  .docx đúng format Azota   → processor.azota_parser           (chính xác, không cần MinerU)
  .docx sai format Azota    → convert_docx_to_pdf + báo dùng MinerU
  .pdf  (--azota-pdf)       → processor.azota_pdf_parser       (PyMuPDF)
  .pdf  thường              → báo dùng pipeline MinerU cũ

Đáp án: ưu tiên BẢNG ĐÁP ÁN (LLM đọc + khớp mã đề) → fallback gạch chân/highlight → regex.
Chéo kiểm tra 2 nguồn; lệch/thiếu → gắn cờ needs_review. Topic/level qua LLM (qwen-turbo) hoặc
keyword. Mọi đề import xong đều cần GIÁO VIÊN REVIEW trước khi giao bài.

Usage:
  python import_azota.py <file.docx|pdf> <CODE> "Tên đề" [năm] [--no-llm] [--azota-pdf]
  CODE ∈ TOAN LY HOA SINH SU DIA GDCD ANH
"""
import re
import shutil
import sys
import io
from pathlib import Path
from typing import Optional

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

import requests
from rich.console import Console
from rich.panel import Panel

from database import db
from processor import subject_structures as ss
from processor import azota_llm
from processor.azota_merge import merge_answers
from import_exam_deepseek import (
    insert_to_supabase, _create_exam_record, SUPABASE_URL,
    SUPABASE_SERVICE_KEY, IMAGE_PUBLIC_DIR,
)

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Upload ảnh (sync) — reuse được fallback local của import_exam_deepseek
# ─────────────────────────────────────────────────────────────────────────────

def _upload_one(abspath: str, folder: str) -> str:
    """Upload 1 ảnh PNG → public URL; fallback copy vào web/public/exam-images."""
    name = Path(abspath).name
    if SUPABASE_SERVICE_KEY:
        storage_path = f"{folder}/{name}"
        url = f"{SUPABASE_URL}/storage/v1/object/exam-images/{storage_path}"
        try:
            with open(abspath, "rb") as f:
                data = f.read()
            headers = {"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}", "Content-Type": "image/png"}
            r = requests.post(url, data=data, headers=headers)
            if r.status_code not in (200, 201):
                r = requests.put(url, data=data, headers=headers)
            if r.status_code in (200, 201):
                return f"{SUPABASE_URL}/storage/v1/object/public/exam-images/{storage_path}"
        except Exception:
            pass
    IMAGE_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGE_PUBLIC_DIR / name
    if not dest.exists():
        shutil.copy2(abspath, dest)
    return f"/exam-images/{name}"


def _publish_images(q, folder: str) -> None:
    """Upload mọi ảnh của câu, thay ![](abspath) → ![](public_url) trong content/options/giải."""
    for abspath in q.image_paths:
        url = _upload_one(abspath, folder)
        old, new = f"]({abspath})", f"]({url})"
        q.question_text = q.question_text.replace(old, new)
        if q.options:
            q.options = {k: v.replace(old, new) for k, v in q.options.items()}
        if q.explanation:
            q.explanation = q.explanation.replace(old, new)


# ─────────────────────────────────────────────────────────────────────────────
# Insert vào production
# ─────────────────────────────────────────────────────────────────────────────

def _insert_exam(exam, title: str, year: int, code: str, subject_id: int) -> tuple[int, int, int]:
    exam_id = _create_exam_record(title, year, subject_id)
    folder = re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:40] + f"-{exam_id}"
    ok = err = review = 0
    for q in exam.questions:
        _publish_images(q, folder)
        options_list = [f"{k}. {v}" for k, v in (q.options or {}).items()]
        final_data = {
            "part": f"part_{q.section}",
            "question_index": q.index,
            "question_text": q.question_text,
            "options": options_list,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "topic": getattr(q, "topic_name", "Chủ đề chung"),
            "level": q.level or "Thông hiểu",
            "raw_content": q.question_text,
            "needs_review": q.needs_review,
            "review_reason": q.review_reason,
        }
        if insert_to_supabase(final_data, exam_id, subject_id):
            ok += 1
            if q.needs_review:
                review += 1
        else:
            err += 1
    return exam_id, ok, err, review


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = [a for a in sys.argv[1:]]
    use_llm = "--no-llm" not in args
    force_pdf = "--azota-pdf" in args
    args = [a for a in args if not a.startswith("--")]

    if len(args) < 2:
        console.print("[red]Usage: python import_azota.py <file.docx|pdf> <CODE> \"Tên đề\" [năm] "
                      "[--no-llm] [--azota-pdf][/]")
        console.print("[dim]CODE ∈ TOAN LY HOA SINH SU DIA GDCD ANH[/]")
        return

    file_path = Path(args[0])
    code = args[1].upper()
    title = args[2] if len(args) > 2 else file_path.stem
    year = int(args[3]) if len(args) > 3 else 2026

    if not file_path.exists():
        console.print(f"[red]Không tìm thấy file: {file_path}[/]")
        return

    db.init_pool()
    subject_id = db.get_subject_id(code)
    if not subject_id:
        console.print(f"[red]Mã môn '{code}' không có trong DB.[/]")
        return

    console.print(Panel(f"[bold]{title}[/] ({year}) — môn {code}\n[dim]{file_path.name}[/]", style="cyan"))

    ext = file_path.suffix.lower()
    exam = None

    if ext == ".docx":
        from processor.azota_parser import parse_azota_docx, is_azota_format
        ok_fmt, diag = is_azota_format(str(file_path))
        if not ok_fmt:
            console.print(f"[yellow]File .docx KHÔNG đúng format Azota[/] {diag}")
            _route_to_mineru(file_path)
            return
        exam = parse_azota_docx(str(file_path))
    elif ext == ".pdf":
        if not force_pdf:
            try:
                from processor.azota_pdf_parser import is_azota_pdf
                ok_fmt, _ = is_azota_pdf(str(file_path))
            except Exception:
                ok_fmt = False
            if not ok_fmt:
                console.print("[yellow]PDF không nhận diện là Azota — dùng pipeline MinerU cũ.[/]")
                console.print("[dim]Hoặc thêm cờ --azota-pdf nếu chắc chắn đây là đề Azota.[/]")
                return
        from processor.azota_pdf_parser import parse_azota_pdf
        exam = parse_azota_pdf(str(file_path))
    else:
        console.print(f"[red]Định dạng {ext} không hỗ trợ (chỉ .docx / .pdf).[/]")
        return

    console.print(f"  Parse: {len(exam.questions)} câu | mã đề {exam.ma_de} | {exam.diagnostics}")

    # ── Đáp án: LLM đọc bảng + khớp mã đề, fallback gạch chân/regex ──────────
    table_answers = azota_llm.extract_answers(exam.raw_answer_block, exam.ma_de, use_llm=use_llm)
    console.print(f"  Bảng đáp án (mã {exam.ma_de}): {len(table_answers)} câu | "
                  f"gạch chân/highlight: {len(exam.fmt_answers)} câu")
    merge_answers(exam, table_answers)

    # ── Validate cấu trúc môn ───────────────────────────────────────────────
    warnings = ss.validate(exam, code)
    for w in warnings:
        console.print(f"  [yellow]⚠ {w}[/]")

    # ── Topic + level (LLM hoặc keyword) ────────────────────────────────────
    azota_llm.enrich_topics_levels(exam.questions, code, use_llm=use_llm)

    # ── Insert ──────────────────────────────────────────────────────────────
    exam_id, ok, err, review = _insert_exam(exam, title, year, code, subject_id)

    console.print(f"\n  [green]Hoàn tất[/] exam_id={exam_id} | [green]{ok} câu[/]"
                  + (f" [red]{err} lỗi[/]" if err else ""))
    if review or warnings:
        console.print(f"  [bold yellow]⚠ {review} câu cần GIÁO VIÊN REVIEW[/] "
                      f"(đáp án lệch/thiếu){' + cảnh báo cấu trúc' if warnings else ''}.")
        for q in exam.questions:
            if q.needs_review:
                console.print(f"    [dim]· P{q.section} Câu {q.index}: {q.review_reason}[/]")
    console.print("  [bold]→ Hãy review đề trước khi giao bài cho học sinh.[/]")
    console.print(f"  [dim]http://localhost:3000/exams[/]\n")


def _route_to_mineru(file_path: Path) -> None:
    """Fallback: convert docx → PDF rồi hướng dẫn chạy pipeline MinerU cũ."""
    out_pdf = file_path.with_suffix(".pdf")
    console.print(f"[cyan]Đang convert sang PDF để đưa qua MinerU: {out_pdf.name}[/]")
    try:
        from convert_docx_to_pdf import convert_docx_to_pdf
        if convert_docx_to_pdf(str(file_path), str(out_pdf)):
            console.print(f"[green]Đã tạo {out_pdf}[/]. Chạy MinerU OCR rồi import bằng pipeline cũ "
                          f"(run_deepseek_all.py).")
        else:
            console.print("[red]Convert thất bại (cần MS Word). Hãy tự xuất PDF rồi dùng MinerU.[/]")
    except Exception as e:
        console.print(f"[red]Không convert được: {e}. Hãy tự xuất PDF rồi dùng MinerU.[/]")


if __name__ == "__main__":
    main()
