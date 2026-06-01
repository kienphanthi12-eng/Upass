"""
processor/azota_merge.py — Trộn đáp án từ nhiều nguồn + gắn cờ needs_review.

Dùng chung bởi import_azota.py (CLI → production) và processor/azota_job.py (web → draft).

Quy tắc:
  - P1/P2: ưu tiên bảng (LLM/regex, đã khớp mã đề) → fallback gạch chân/highlight.
           Nếu cả hai nguồn có mà LỆCH → giữ bảng + needs_review.
  - P3:    đáp án từ "Đáp án:" inline (đã có ở câu); bảng để đối chiếu, lệch → needs_review.
  - Thiếu đáp án ở bất kỳ câu nào → needs_review.
"""
from __future__ import annotations

import re
from typing import Optional


def norm(s: Optional[str]) -> str:
    return re.sub(r"\s+", "", (s or "")).upper()


def merge_answers(exam, table_answers: dict) -> None:
    """Điền q.correct_answer + gắn q.needs_review/q.review_reason cho từng câu của exam."""
    for q in exam.questions:
        key = (q.section, q.index)
        table = table_answers.get(key)
        fmt = exam.fmt_answers.get(key)

        if q.section == 3:
            if not q.correct_answer and table:
                q.correct_answer = table
            elif q.correct_answer and table and norm(q.correct_answer) != norm(table):
                q.needs_review, q.review_reason = True, f"P3 inline({q.correct_answer})≠bảng({table})"
        else:
            if table and fmt and norm(table) != norm(fmt):
                q.correct_answer = table
                q.needs_review, q.review_reason = True, f"bảng({table})≠gạch chân({fmt})"
            elif table:
                q.correct_answer = table
            elif fmt:
                q.correct_answer = fmt

        if not q.correct_answer:
            q.needs_review = True
            q.review_reason = (q.review_reason + "; " if q.review_reason else "") + "thiếu đáp án"
