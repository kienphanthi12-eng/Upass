"""
processor/azota_pdf_parser.py — Parser PDF cho đề soạn theo format Azota (PyMuPDF).

Pipeline PDF "hoàn toàn mới" (không OCR — đọc text layer + hình học của PDF):
  - Text + tọa độ:  page.get_text("dict")  → tách phần/câu/options theo dòng.
  - Bảng đáp án:     page.find_tables()      → raw_answer_block (ưu tiên, LLM/regex đọc).
  - Gạch chân:       page.get_drawings()     → đường ngang dưới span = đáp án đúng.
  - Highlight:       page.annots() + rect tô màu.
  - Mã đề:           regex từ text header.

Trả về AzotaExam (cùng dataclass với azota_parser) → dùng chung downstream (validate, LLM,
merge, insert). Lưu ý: công thức dạng vector/ảnh trong PDF có thể không vào được text layer —
khuyến nghị giáo viên dùng bản .docx cho đề nhiều công thức (xem giới hạn trong plan).
"""
from __future__ import annotations

import re
from typing import Optional

import fitz  # PyMuPDF

from .azota_parser import (
    AzotaExam, AzotaQuestion, _QBuilder,
    _RE_SECTION, _RE_QUESTION, _RE_OPT_ABCD, _RE_SUBITEM, _RE_TLN_ANSWER,
    _RE_LEVEL_PREFIX, _RE_MA_DE, _RE_END, _RE_SOLUTION,
    _split_options, _normalize_tln, _strip_question_prefix,
    _SECTION_QTYPE, _LEVEL_CODE, _ROMAN,
)


# ─────────────────────────────────────────────────────────────────────────────
# LINE MODEL + ĐÁNH DẤU (gạch chân / highlight)
# ─────────────────────────────────────────────────────────────────────────────

class _Line:
    __slots__ = ("text", "y", "x", "page", "spans", "marked")

    def __init__(self, text, y, x, page, spans, marked):
        self.text = text
        self.y = y
        self.x = x
        self.page = page
        self.spans = spans          # [(text, bbox)]
        self.marked = marked        # True nếu có span gạch chân/highlight


def _horizontal_marks(page) -> list[tuple[float, float, float, float]]:
    """Lấy các đoạn 'gạch chân' (line ngang mảnh hoặc rect mảnh) + vùng highlight → bbox list."""
    marks: list[tuple[float, float, float, float]] = []
    try:
        for d in page.get_drawings():
            for item in d.get("items", []):
                if item[0] == "l":  # line: (p1, p2)
                    p1, p2 = item[1], item[2]
                    if abs(p1.y - p2.y) <= 1.5 and abs(p1.x - p2.x) >= 6:
                        x0, x1 = sorted((p1.x, p2.x))
                        marks.append((x0, min(p1.y, p2.y), x1, max(p1.y, p2.y)))
                elif item[0] == "re":  # rect: có thể là gạch chân dày hoặc highlight
                    r = item[1]
                    if r.height <= 4 and r.width >= 6:           # đường gạch
                        marks.append((r.x0, r.y0, r.x1, r.y1))
                    elif d.get("fill") and r.height <= 24 and r.width >= 10:  # ô tô màu
                        marks.append((r.x0, r.y0, r.x1, r.y1))
    except Exception:
        pass
    # Highlight annotations
    try:
        annot = page.first_annot
        while annot:
            if annot.type[0] == 8:  # Highlight
                r = annot.rect
                marks.append((r.x0, r.y0, r.x1, r.y1))
            annot = annot.next
    except Exception:
        pass
    return marks


def _span_marked(span_bbox, marks) -> bool:
    """True nếu span có đường gạch ngay dưới (hoặc nằm trong vùng tô màu)."""
    sx0, sy0, sx1, sy1 = span_bbox
    span_w = max(sx1 - sx0, 1)
    for mx0, my0, mx1, my1 in marks:
        # x-overlap đáng kể
        ox = min(sx1, mx1) - max(sx0, mx0)
        if ox < span_w * 0.4:
            continue
        # gạch chân: đường nằm trong nửa dưới span đến ngay dưới baseline
        if sy0 <= my0 <= sy1 + 4:
            return True
        # highlight: bao phủ theo trục y
        if my0 <= (sy0 + sy1) / 2 <= my1:
            return True
    return False


def _extract_lines(doc) -> list[_Line]:
    """Trích toàn bộ dòng text (kèm cờ marked) theo thứ tự trang → trên-xuống → trái-phải."""
    lines: list[_Line] = []
    for pno in range(len(doc)):
        page = doc.load_page(pno)
        marks = _horizontal_marks(page)
        data = page.get_text("dict")
        page_lines = []
        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            for ln in block.get("lines", []):
                spans = ln.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans)
                if not text.strip():
                    continue
                span_info = [(s["text"], tuple(s["bbox"])) for s in spans]
                marked = any(_span_marked(s["bbox"], marks) for s in spans if s["text"].strip())
                x0 = min(s["bbox"][0] for s in spans)
                y0 = min(s["bbox"][1] for s in spans)
                page_lines.append(_Line(text, y0, x0, pno, span_info, marked))
        page_lines.sort(key=lambda l: (round(l.y), l.x))
        lines.extend(page_lines)
    return lines


def _marked_letters_in_line(line: _Line, letter_re: re.Pattern) -> set[str]:
    """Suy nhãn (A-D/a-d) được đánh dấu trong 1 dòng, dựa trên span marked + vị trí marker."""
    out: set[str] = set()
    current: Optional[str] = None
    for text, bbox in line.spans:
        for m in re.finditer(r"([A-Da-d])[.)]", text):
            current = m.group(1)
        # span này marked?
        # (đã tính marked tổng cho line; ở đây xấp xỉ: nếu line.marked và current có → gán)
    if line.marked:
        # tìm nhãn đầu tiên trong dòng làm đại diện (đa số option 1 dòng = 1 nhãn)
        m = letter_re.match(line.text) or re.search(r"([A-Da-d])[.)]", line.text)
        if m:
            out.add(m.group(1))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# ANSWER TABLES
# ─────────────────────────────────────────────────────────────────────────────

def _extract_answer_tables(doc) -> str:
    """Lấy text mọi bảng trong PDF (ưu tiên trang cuối) để LLM/regex đọc bảng đáp án."""
    chunks: list[str] = []
    for pno in range(len(doc)):
        page = doc.load_page(pno)
        try:
            tabs = page.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            rows = t.extract()
            lines = [" | ".join((c or "").strip().replace("\n", " ") for c in row) for row in rows]
            chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PARSE
# ─────────────────────────────────────────────────────────────────────────────

def parse_azota_pdf(path: str) -> AzotaExam:
    """Parse PDF soạn theo format Azota → AzotaExam (text-based, không OCR)."""
    doc = fitz.open(path)
    exam = AzotaExam()

    lines = _extract_lines(doc)
    full_head = "\n".join(l.text for l in lines[:60])
    mm = _RE_MA_DE.search(full_head)
    if mm:
        exam.ma_de = mm.group(1)

    section = 0
    builder: Optional[_QBuilder] = None
    in_answer_region = False
    seen_question = False

    def flush():
        nonlocal builder
        if builder is not None:
            q = builder.finalize()
            if builder.marked:
                if builder.section == 2:
                    code = "".join("D" if c in builder.marked else "S" for c in "abcd")
                    exam.fmt_answers[(2, builder.index)] = code
                else:
                    letters = sorted(L for L in builder.marked if L in "ABCD")
                    if letters:
                        exam.fmt_answers[(builder.section, builder.index)] = "".join(letters)
            exam.questions.append(q)
            builder = None

    for line in lines:
        text = line.text.strip()
        if not text:
            continue

        if not in_answer_region and _RE_END.search(text):
            flush()
            in_answer_region = True
            continue
        if in_answer_region:
            continue  # bảng đáp án lấy riêng qua _extract_answer_tables

        ms = _RE_SECTION.match(text)
        if ms:
            flush()
            section = _ROMAN.get(ms.group(1).upper(), section + 1)
            continue

        mq = _RE_QUESTION.match(text)
        if mq:
            flush()
            seen_question = True
            if section == 0:
                section = 1
            builder = _QBuilder(section, int(mq.group(1)))
            rest = mq.group(2).strip()
            ml = _RE_LEVEL_PREFIX.match(rest)
            if ml:
                builder.level = _LEVEL_CODE.get(ml.group(2).upper())
            stem_line = _strip_question_prefix(text)
            if ml:
                stem_line = _RE_LEVEL_PREFIX.sub("", stem_line, count=1)
            builder.stem_parts.append(stem_line)
            continue

        if builder is None:
            continue

        if _RE_SOLUTION.match(text):
            builder.in_solution = True
            after = _RE_SOLUTION.sub("", text, count=1).strip(" .:–-")
            if after:
                builder.explanation_parts.append(after)
            continue
        if builder.in_solution:
            builder.explanation_parts.append(text)
            continue

        if builder.section == 3:
            mt = _RE_TLN_ANSWER.search(text)
            if mt:
                builder.tln_answer = _normalize_tln(mt.group(1))
                continue

        is_opt = (builder.section != 3) and (
            _RE_OPT_ABCD.match(text) or _RE_SUBITEM.match(text)
            or bool(re.search(r"\s{2,}[A-Da-d][.)]", text))
        )
        if is_opt:
            builder.option_text_parts.append(text)
            letter_re = _RE_SUBITEM if builder.section == 2 else _RE_OPT_ABCD
            builder.marked |= _marked_letters_in_line(line, letter_re)
            continue

        builder.stem_parts.append(text)

    flush()

    exam.raw_answer_block = _extract_answer_tables(doc)
    doc.close()

    exam.diagnostics = {
        "n_questions": len(exam.questions),
        "n_sections": len({q.section for q in exam.questions}),
        "has_answer_block": bool(exam.raw_answer_block),
        "n_fmt_answers": len(exam.fmt_answers),
    }
    return exam


def is_azota_pdf(path: str) -> tuple[bool, dict]:
    """Kiểm tra PDF có text layer dạng Azota (đủ câu 'Câu N.' + phần/bảng)."""
    try:
        doc = fitz.open(path)
    except Exception as e:
        return False, {"error": str(e)}
    n_q = n_sec = 0
    has_end = False
    has_table = False
    for pno in range(len(doc)):
        page = doc.load_page(pno)
        txt = page.get_text("text")
        n_q += len(re.findall(r"(?:^|\n)\s*(?:Câu|Cau|Bài|Question)\s*\d+\s*[.:]", txt, re.I))
        n_sec += len(_RE_SECTION.findall(txt)) if False else len(re.findall(r"PH[ẦA]N\s+(?:I{1,3}|[1-3])", txt, re.I))
        if _RE_END.search(txt):
            has_end = True
        try:
            if page.find_tables().tables:
                has_table = True
        except Exception:
            pass
    doc.close()
    diag = {"n_questions": n_q, "n_sections": n_sec, "has_end_marker": has_end, "has_table": has_table}
    ok = n_q >= 5 and (n_sec >= 1 or has_end or has_table)
    diag["is_azota"] = ok
    return ok, diag
