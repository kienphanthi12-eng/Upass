"""
processor/subject_structures.py — Cấu trúc đề thi tốt nghiệp THPT 2025 theo từng môn.

Dùng để validate đề đã parse: kiểm tra số câu mỗi phần có khớp cấu trúc chuẩn không.
Không chặn import — chỉ trả về danh sách cảnh báo để giáo viên review.

Cấu trúc 3 phần (định dạng GDPT 2018, áp dụng từ 2025):
  - Phần I  : Trắc nghiệm nhiều lựa chọn (chọn 1 trong 4)        → section 1
  - Phần II : Trắc nghiệm đúng/sai (4 ý a,b,c,d mỗi câu)         → section 2
  - Phần III: Trắc nghiệm trả lời ngắn                           → section 3

Mã môn khớp bảng `subjects` trong DB (code).
"""
from __future__ import annotations

from typing import Optional


# code → cấu trúc chuẩn. p1/p2/p3 = số câu mỗi phần; total = tổng; minutes = thời gian.
STRUCTURES: dict[str, dict] = {
    "TOAN":  {"name": "Toán",      "p1": 12, "p2": 4, "p3": 6, "total": 22, "minutes": 90},
    "LY":    {"name": "Vật Lý",    "p1": 18, "p2": 4, "p3": 6, "total": 28, "minutes": 50},
    "HOA":   {"name": "Hóa Học",   "p1": 18, "p2": 4, "p3": 6, "total": 28, "minutes": 50},
    "SINH":  {"name": "Sinh Học",  "p1": 18, "p2": 4, "p3": 6, "total": 28, "minutes": 50},
    "SU":    {"name": "Lịch Sử",   "p1": 24, "p2": 4, "p3": 0, "total": 28, "minutes": 50},
    "DIA":   {"name": "Địa Lý",    "p1": 24, "p2": 4, "p3": 0, "total": 28, "minutes": 50},
    # GDKT&PL (Giáo dục Kinh tế & Pháp luật) dùng slot GDCD trong DB
    "GDCD":  {"name": "GD KT&PL",  "p1": 24, "p2": 4, "p3": 0, "total": 28, "minutes": 50},
    # Tiếng Anh: 40 câu trắc nghiệm thuần (đọc hiểu, điền từ…), không chia 3 phần
    "ANH":   {"name": "Tiếng Anh", "p1": 40, "p2": 0, "p3": 0, "total": 40, "minutes": 50},
}


def get_structure(code: str) -> Optional[dict]:
    """Trả về cấu trúc chuẩn của môn, hoặc None nếu chưa định nghĩa."""
    return STRUCTURES.get((code or "").upper())


def count_by_section(exam) -> dict[int, int]:
    """Đếm số câu theo section (1/2/3) từ AzotaExam (duck-typed: cần .questions[].section)."""
    counts: dict[int, int] = {1: 0, 2: 0, 3: 0}
    for q in getattr(exam, "questions", []):
        sec = getattr(q, "section", 1)
        counts[sec] = counts.get(sec, 0) + 1
    return counts


def validate(exam, code: str) -> list[str]:
    """
    So số câu mỗi phần của đề đã parse với cấu trúc chuẩn của môn.

    Trả về list cảnh báo (rỗng nếu khớp hoàn toàn). KHÔNG raise — chỉ cảnh báo.
    """
    struct = get_structure(code)
    if not struct:
        return [f"Chưa có cấu trúc chuẩn cho môn '{code}' — bỏ qua validate."]

    counts = count_by_section(exam)
    warnings: list[str] = []

    expected = {1: struct["p1"], 2: struct["p2"], 3: struct["p3"]}
    labels = {1: "Phần I (trắc nghiệm)", 2: "Phần II (đúng/sai)", 3: "Phần III (trả lời ngắn)"}

    for sec in (1, 2, 3):
        exp = expected[sec]
        got = counts.get(sec, 0)
        if got != exp:
            if exp == 0 and got > 0:
                warnings.append(
                    f"{labels[sec]}: có {got} câu nhưng môn {struct['name']} không có phần này."
                )
            else:
                warnings.append(
                    f"{labels[sec]}: {got} câu, kỳ vọng {exp} câu."
                )

    total_got = sum(counts.values())
    if total_got != struct["total"]:
        warnings.append(
            f"Tổng: {total_got} câu, kỳ vọng {struct['total']} câu "
            f"(đề chuẩn {struct['name']}, {struct['minutes']} phút)."
        )

    return warnings
