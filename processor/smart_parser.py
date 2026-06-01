"""
smart_parser.py — Bộ parser linh hoạt cho đề thi THPT (Toán, Lý, Hóa, Anh, ...).

Thiết kế:
  • Không hardcode số câu — tự detect dynamic từ nội dung.
  • Xử lý được file chứa nhiều đề.
  • Không dùng LLM — thuần regex + heuristics.

Pipeline 3 tầng:
  L1: Document Split  — tách {exam_body / answer_table / solution}
  L2: Question Split  — tìm ranh giới từng câu (flexible, OCR-aware)
  L3: Content Parse   — phân loại + extract options, ghép đáp án + lời giải
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RawQuestion:
    index: int                   # Số thứ tự trong đề (1, 2, 3 …)
    section: int                 # 1 / 2 / 3 (Phần I/II/III)
    q_type: str                  # "trac_nghiem" | "dung_sai" | "tu_luan"
    raw_text: str                # Toàn bộ text block của câu (kể cả options)
    question_text: str           # Chỉ phần đề bài (đã bỏ options + prefix)
    options: Optional[dict]      # {"A": "…", "B": "…"} hoặc {"a": "…", …}
    correct_answer: Optional[str]
    explanation: Optional[str]
    image_paths: list[str]


@dataclass
class ParsedExam:
    ma_de: str
    subject: str                 # "TOAN" | "VAT_LI" | "HOA_HOC" | …
    questions: list[RawQuestion] = field(default_factory=list)
    raw_answer_block: str = ""   # Raw text của bảng đáp án
    raw_solution: str = ""       # Raw text của phần lời giải


# ─────────────────────────────────────────────────────────────────────────────
# L1: DOCUMENT SPLIT — tách exam_body / answer_table / solution
# ─────────────────────────────────────────────────────────────────────────────

# Anchors đánh dấu bắt đầu phần LỜI GIẢI / ĐÁP ÁN
_SOLUTION_ANCHORS: list[str] = [
    # Lời giải tham khảo — tin cậy nhất
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?L[ỜO]I\s+GI[ẢA]I\s+THAM\s+KH[ẢA]O",
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?LOI\s+GIAI\s+THAM\s+KHAO",
    # Hướng dẫn giải chi tiết
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?H[ƯỚUƠ]NG\s+D[ẪÃA]N\s+GI[ẢA]I\s+CHI\s+TI[ẾE]T",
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?HUONG\s+DAN\s+GIAI\s+CHI\s+TIET",
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?H[ƯỚUƠ]NG\s+D[ẪÃA]N\s+GI[ẢA]I",
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?HUONG\s+DAN\s+GIAI",
    # Đáp án - lời giải
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?[ĐD][ÁAÀ]P\s+[ÁAÀ]N\s+[-–]\s+L[ỜO]I\s+GI[ẢA]I",
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?DAP\s+AN\s+[-–]\s+LOI\s+GIAI",
    # Đáp án chi tiết
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?[ĐD][ÁAÀ]P\s+[ÁAÀ]N\s+CHI\s+TI[ẾE]T",
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?DAP\s+AN\s+CHI\s+TIET",
    # Đáp án tham khảo
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?[ĐD][ÁAÀ]P\s+[ÁAÀ]N\s+THAM\s+KH[ẢA]O",
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?DAP\s+AN\s+THAM\s+KHAO",
    # Lời giải chi tiết / Bài giải chi tiết
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?(?:L[ỜO]I\s+GI[ẢA]I|B[ÀA]I\s+GI[ẢA]I)\s+CHI\s+TI[ẾE]T",
    r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?(?:LOI\s+GIAI|BAI\s+GIAI)\s+CHI\s+TIET",
]

# Anchors đánh dấu KẾT THÚC đề thi (trước phần đáp án)
_END_ANCHORS: list[str] = [
    r"(?i)-{2,}\s*H[ẾE]T\s*-{2,}",
    r"(?i)-{2,}\s*HT\s*-{2,}",
    r"(?i)\*{2,}\s*H[ẾE]T\s*\*{2,}",
    r"(?i)---+\s*END\s*---+",
    # Hết / HẾT ĐỀ / HẾT. / END độc lập trên dòng
    r"(?i)(?:^|\n)\s*[-–—_*\s]*\s*H[ẾE]T\s*[-–—_*\s]*(?:\n|$)",
    r"(?i)(?:^|\n)\s*[-–—_*\s]*\s*HÊT\s*[-–—_*\s]*(?:\n|$)",
    r"(?i)(?:^|\n)\s*[-–—_*\s]*\s*END\s*[-–—_*\s]*(?:\n|$)",
]

# Anchors đánh dấu bắt đầu 1 đề mới (dùng cho multi-exam detection)
_EXAM_HEADER_ANCHORS: list[str] = [
    r"(?i)(?:^|\n)\s*(?:#{1,2}\s*)?S[ỞO]\s+GI[ÁA]O\s+D[ỤU]C",
    r"(?i)(?:^|\n)\s*(?:#{1,2}\s*)?K[ÌỲY]\s+THI\s+",
    r"(?i)(?:^|\n)\s*(?:#{1,2}\s*)?KY\s+THI\s+",
    r"(?i)(?:^|\n)\s*M[ÃA]\s+[ĐD][ÊE]\s+\d{3,4}",
    r"(?i)(?:^|\n)\s*Ma\s+de\s+\d{3,4}",
]


def _find_earliest(text: str, patterns: list[str]) -> int:
    """Trả về vị trí xuất hiện sớm nhất trong text của bất kỳ pattern nào."""
    best = len(text)
    for p in patterns:
        for m in re.finditer(p, text, re.MULTILINE):
            if m.start() < best:
                best = m.start()
    return best


def _find_answer_table_pos(text: str) -> int:
    """
    Tìm vị trí bắt đầu của bảng đáp án HTML.
    Chiến lược: tìm <table> mà:
      - Header chứa "câu" / "cau" / "dap an"  (standard)
      - HOẶC header là số nguyên (1, 2, 3...) → bảng đáp án số liên tục
      - HOẶC header là dạng sub-item (1a, 1b, 2a...) → Phần II đúng/sai
    """
    best = len(text)
    for m in re.finditer(r"<table[\s\S]+?</table>", text, re.I):
        head_html = m.group(0)[:800]
        cells = re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", head_html, re.I)
        cell_texts_raw = [re.sub(r"<[^>]+>", "", c).strip() for c in cells[:10]]
        cell_texts_joined = " ".join(cell_texts_raw)

        is_answer_table = (
            # Standard: có chứa "câu" / "cau" / "đáp án"
            re.search(r"c[aâ][uư]|cau|[dđ][aáà]p\s*[aáà]n", cell_texts_joined, re.I)
            # Numeric header: các cell đầu là số liên tục (1 2 3 4 5 ...)
            or _is_numeric_header(cell_texts_raw[:8])
            # Sub-item header: 1a 1b 1c 1d 2a 2b ...
            or _is_subitem_header(cell_texts_raw[:8])
        )

        if is_answer_table and m.start() < best:
            best = m.start()
    return best


def _is_numeric_header(cells: list[str]) -> bool:
    """True nếu các cells đầu tiên là số liên tục (bảng đáp án số)."""
    nums = []
    for c in cells:
        s = c.strip()
        if re.fullmatch(r"\d+", s):
            nums.append(int(s))
        else:
            break
    return len(nums) >= 4 and nums == list(range(nums[0], nums[0] + len(nums)))


def _is_subitem_header(cells: list[str]) -> bool:
    """True nếu cells là dạng 1a, 1b, 1c, 2a, 2b... (bảng Phần II đúng/sai)."""
    count = sum(1 for c in cells if re.fullmatch(r"\d+[abcdABCD]", c.strip()))
    return count >= 3


def split_document(raw_text: str) -> tuple[str, str, str]:
    """
    Tách 1 đề thi thành 3 phần:
      (exam_body, answer_block_raw, solution_raw)

    Thuật toán:
      1. Tìm vị trí bắt đầu phần lời giải → solution_start
      2. Trong [0:solution_start], tìm bảng đáp án → ans_start
      3. exam_body = text[:ans_start]
    """
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Tìm phần lời giải
    sol_start = _find_earliest(text, _SOLUTION_ANCHORS)

    # Fallback: tìm HẾT nếu không có lời giải
    if sol_start == len(text):
        sol_start = _find_earliest(text, _END_ANCHORS)

    body_and_ans = text[:sol_start]
    solution_raw = text[sol_start:]

    # Tìm bảng đáp án trong phần đề + đáp án
    ans_start = _find_answer_table_pos(body_and_ans)

    # Fallback: tìm heading "ĐÁP ÁN" standalone
    if ans_start == len(body_and_ans):
        ans_start = _find_earliest(body_and_ans, [
            r"(?i)(?:^|\n)\s*[ĐD][ÁAÀ]P\s+[ÁAÀ]N\s*\n",
            r"(?i)(?:^|\n)\s*DAP\s+AN\s*\n",
            # Phan I: (với dấu hai chấm = bảng đáp án)
            r"(?i)(?:^|\n)\s*Phan\s+I\s*:",
            r"(?i)(?:^|\n)\s*PH[ẦÀA]N\s+I\s*:",
        ])

    exam_body = body_and_ans[:ans_start].strip()
    answer_block = body_and_ans[ans_start:].strip()

    return exam_body, answer_block, solution_raw.strip()


# ─────────────────────────────────────────────────────────────────────────────
# MULTI-EXAM: Detect nhiều đề trong 1 file
# ─────────────────────────────────────────────────────────────────────────────

def split_multi_exam(raw_text: str) -> list[str]:
    """
    Kiểm tra xem file có chứa nhiều đề không.
    - Nếu có → chia thành list[str] cho từng đề.
    - Nếu không → trả về [raw_text].

    Heuristic: tìm các vị trí header "SỞ GIÁO DỤC" / "KỲ THI" cách nhau > 3000 chars.
    """
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    starts: list[int] = []
    for p in _EXAM_HEADER_ANCHORS:
        for m in re.finditer(p, text, re.MULTILINE):
            starts.append(m.start())

    if not starts:
        return [text]

    starts = sorted(set(starts))

    # Lọc: chỉ giữ những start cách nhau > 3000 chars (tránh false positive)
    filtered: list[int] = [starts[0]]
    for s in starts[1:]:
        if s - filtered[-1] > 3000:
            filtered.append(s)

    if len(filtered) <= 1:
        return [text]

    # Chia thành các đề riêng biệt
    exams: list[str] = []
    for i, s in enumerate(filtered):
        end = filtered[i + 1] if i + 1 < len(filtered) else len(text)
        chunk = text[s:end].strip()
        if chunk:
            exams.append(chunk)

    return exams if exams else [text]


# ─────────────────────────────────────────────────────────────────────────────
# L2: SECTION & QUESTION DETECTION
# ─────────────────────────────────────────────────────────────────────────────

# "Câu N" — chịu được OCR noise: Cau/Câu/CAU/cau + số
_CAU_PAT = re.compile(
    r"(?:"
    # Cách 1: Ở đầu dòng (chấp nhận cả chữ thường, dấu phân cách tùy ý)
    r"(?:^|\n)\s*(?:[Cc][aâ][uư]?|CAU|C[ÂA]U|[Qq]?uestion|[Qq]?uest|QUESTION|QUEST)\s*\.?\s*(\d+)\s*[.:\-–]?\s*"
    r"|"
    # Cách 2: Ở giữa dòng (bắt buộc viết hoa chữ C/Q và có dấu phân cách rõ ràng để tránh false positive)
    r"\b(?:[Cc][aâ][uư]?|CAU|C[ÂA]U|[Qq]?uestion|[Qq]?uest|QUESTION|QUEST)\s*\.?\s*(\d+)\s*[.:\-–]\s*"
    r")"
    r"(?=\D|$)",
    re.MULTILINE,
)

# PHAN I / PHAN II / PHAN III — flexible (supports OCR noise like I1, 11, ll, etc.)
_SECTION_PAT = re.compile(
    r"(?:^|\n)"
    r"\s*(?:#{1,3}\s*)?"
    r"(?:PH[ẦÀA]N|PHN|PHAN|Ph[ầà]n)"
    r"\s*"
    r"([a-zA-Z0-9|]{1,4})"         # group(1): số phần (có thể có OCR noise)
    r"(?=[\s.:–\-]|$)",
    re.IGNORECASE | re.MULTILINE,
)

_ROMAN: dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4,
    "1": 1, "2": 2, "3": 3, "4": 4,
}

def _determine_section_from_text(heading_line: str, match_index: int) -> int:
    line_lower = heading_line.lower()
    
    # Check Section 2 indicators
    if any(k in line_lower for k in ["dung hoac sai", "dung sai", "dung/sai", "đúng hoặc sai", "đúng sai", "đúng/sai", "chon dung hoac sai"]):
        return 2
    if "cau 4" in line_lower or "câu 4" in line_lower or "4 câu" in line_lower or "4 cau" in line_lower:
        if "câu 18" not in line_lower and "cau 18" not in line_lower and "câu 24" not in line_lower and "cau 24" not in line_lower:
            return 2
            
    # Check Section 3 indicators
    if any(k in line_lower for k in ["tra loi ngan", "trả lời ngắn", "tu luan", "tự luận", "ngan", "ngắn"]):
        return 3
    if "cau 6" in line_lower or "câu 6" in line_lower or "6 câu" in line_lower or "6 cau" in line_lower:
        return 3
        
    # Check Section 1 indicators
    if any(k in line_lower for k in ["trac nghiem", "trắc nghiệm", "nhieu lua chon", "nhiều lựa chọn", "chon mot phuong an"]):
        return 1
    if "18 câu" in line_lower or "18 cau" in line_lower or "18" in line_lower or "24" in line_lower or "40" in line_lower:
        return 1
        
    # Fallback to roman numeral parsing
    m = re.search(r"(III|II|IV|I|3|2|1|11|111|I1|1I|l1|1l|ll|lll|L)", heading_line, re.I)
    if m:
        val = m.group(1).upper()
        # Clean common OCR duplicates
        val = val.replace('L', 'I').replace('1', 'I').replace('|', 'I').replace('l', 'I')
        if "III" in val:
            return 3
        if "II" in val:
            return 2
        if "I" in val:
            return 1
            
    # Sequential fallback based on match index (0-based)
    return match_index + 1

def detect_sections(exam_body: str) -> dict[int, str]:
    """
    Tách exam_body thành {section_num: text}.
    Nếu không tìm thấy header → {1: toàn bộ text}.
    """
    matches = list(_SECTION_PAT.finditer(exam_body))
    if not matches:
        return {1: exam_body}

    # Lọc matches để chỉ giữ lại các section tăng dần (bỏ qua page headers trùng lặp)
    filtered_matches = []
    max_sec = 0
    for i, m in enumerate(matches):
        start_line_pos = exam_body.rfind("\n", 0, m.start()) + 1
        end_line_pos = exam_body.find("\n", m.end())
        if end_line_pos == -1:
            end_line_pos = len(exam_body)
        heading_line = exam_body[start_line_pos:end_line_pos]

        sec_num = _determine_section_from_text(heading_line, i)
        if sec_num >= max_sec:
            max_sec = sec_num
            filtered_matches.append((sec_num, m))

    sections: dict[int, str] = {}
    for idx, (sec_num, m) in enumerate(filtered_matches):
        start = m.end()
        end = filtered_matches[idx + 1][1].start() if idx + 1 < len(filtered_matches) else len(exam_body)
        content = exam_body[start:end].strip()

        if sec_num in sections:
            sections[sec_num] += "\n\n" + content
        else:
            sections[sec_num] = content

    return sections


def detect_questions(section_text: str, section_num: int) -> list[dict]:
    """
    Tìm tất cả câu hỏi trong 1 phần — không giả định số câu.
    Trả về list[dict] với keys: index, section, raw.
    """
    matches = list(_CAU_PAT.finditer(section_text))
    if not matches:
        return []

    questions: list[dict] = []
    for i, m in enumerate(matches):
        q_num = int(m.group(1) or m.group(2))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        raw = section_text[start:end].strip()

        if len(raw) < 10:  # bỏ qua block quá ngắn (false positive)
            continue

        questions.append({
            "index": q_num,
            "section": section_num,
            "raw": raw,
        })

    return questions


# ─────────────────────────────────────────────────────────────────────────────
# L3: CONTENT CLASSIFICATION & PARSE
# ─────────────────────────────────────────────────────────────────────────────

# Options trắc nghiệm: A. / A) / A: — dạng xuống dòng (hỗ trợ mất khoảng trắng)
_OPT_ABCD_NL = re.compile(
    r"(?:^|\n)\s*([ABCD])[.)]\s*(.+?)(?=\n\s*[ABCD][.)]|\Z)",
    re.DOTALL | re.MULTILINE,
)

# Options trắc nghiệm inline: "A. text B. text C. text D. text" (hỗ trợ mất khoảng trắng)
_OPT_ABCD_INLINE = re.compile(
    r"\bA[.)]\s*(.+?)\s*B[.)]\s*(.+?)\s*C[.)]\s*(.+?)\s*D[.)]\s*(.+?)(?=\s*$|\Z)",
    re.DOTALL,
)

# Options đúng/sai: a. / a) / a: (hỗ trợ mất khoảng trắng)
_OPT_abcd = re.compile(
    r"(?:^|\n)\s*([abcd])[.)]\s*(.+?)(?=\n\s*[abcd][.)]|\Z)",
    re.DOTALL | re.MULTILINE,
)

# Prefix "Câu N." / "Câu N:" ở đầu raw_text (hỗ trợ Question)
_CAU_PREFIX = re.compile(
    r"^(?:[Cc][aâ][uư]?|[Qq]?uestion|[Qq]?uest)\s*\d+\s*[.:\-–]?\s*",
    re.IGNORECASE | re.MULTILINE,
)


def classify_and_parse(q: dict) -> dict:
    """
    Phân loại loại câu và extract question_text + options.
    Tự nhận diện từ nội dung — không phụ thuộc vào section number.
    Hỗ trợ cả dạng options xuống dòng lẫn inline cùng dòng (OCR noise).
    """
    raw = q["raw"]

    # ── Thử options xuống dòng trước (reliable nhất) ─────────────────────
    abcd_nl_matches = list(_OPT_ABCD_NL.finditer(raw))
    abcd_nl_keys = {m.group(1).upper() for m in abcd_nl_matches}

    abcd_lower_matches = list(_OPT_abcd.finditer(raw))
    abcd_lower_keys = {m.group(1) for m in abcd_lower_matches}

    # ── Trắc nghiệm options xuống dòng ──────────────────────────────────────
    if len(abcd_nl_keys) >= 3:
        q_type = "trac_nghiem"
        first_opt_start = abcd_nl_matches[0].start()
        question_text = _CAU_PREFIX.sub("", raw[:first_opt_start], count=1).strip()
        options = {
            m.group(1).upper(): re.sub(r"\s+", " ", m.group(2)).strip()
            for m in abcd_nl_matches
        }

    # ── Trắc nghiệm options inline (A. ... B. ... C. ... D. ...) ────────────
    elif m_inline := _OPT_ABCD_INLINE.search(raw):
        q_type = "trac_nghiem"
        question_text = _CAU_PREFIX.sub("", raw[:m_inline.start()], count=1).strip()
        groups = [g.strip() for g in m_inline.groups()]
        options = {k: v for k, v in zip("ABCD", groups) if v}

    # ── Đúng/Sai: có ≥ 3 options a/b/c/d ───────────────────────────────────
    elif len(abcd_lower_keys) >= 3:
        q_type = "dung_sai"
        first_opt_start = abcd_lower_matches[0].start()
        question_text = _CAU_PREFIX.sub("", raw[:first_opt_start], count=1).strip()
        options = {
            m.group(1).lower(): re.sub(r"\s+", " ", m.group(2)).strip()
            for m in abcd_lower_matches
        }

    # ── Tự luận: không có options ───────────────────────────────────────────
    else:
        q_type = "tu_luan"
        question_text = _CAU_PREFIX.sub("", raw, count=1).strip()
        options = None

    image_paths = re.findall(r"!\[[^\]]*\]\((images/[^)]+)\)", raw)

    q.update({
        "q_type": q_type,
        "question_text": question_text,
        "options": options,
        "image_paths": image_paths,
        "correct_answer": None,
        "explanation": None,
    })
    return q


# ─────────────────────────────────────────────────────────────────────────────
# ANSWER TABLE PARSER
# ─────────────────────────────────────────────────────────────────────────────

def _get_cells(row_html: str) -> list[str]:
    cells = re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", row_html, re.I)
    return [re.sub(r"<[^>]+>", "", c).strip() for c in cells]


def _clean_answer(val: str, section: int) -> Optional[str]:
    """Validate + normalize đáp án theo section."""
    v = re.sub(r"\s+", "", val).upper()
    if not v:
        return None

    # Phần I: A/B/C/D
    if section == 1 and re.fullmatch(r"[ABCD]", v):
        return v

    # Phần II: DSDD / DDDS / ... (4 ký tự D/S/Đ)
    if section == 2:
        # Normalize Đ → D
        v2 = v.replace("Đ", "D")
        if re.fullmatch(r"[DS]{4}", v2):
            return v2
        # Verbose format: "Đ S D S" hoặc "D S D S" tách ra
        letters = re.findall(r"[ĐDS]", val, re.I)
        if len(letters) == 4:
            return "".join("D" if l.upper() in "ĐD" else "S" for l in letters)
        # "Dung Sai Dung Sai" / "Đúng Sai" format
        dung_sai = re.findall(r"D[uú]ng|Đ[uú]ng|Sai", val, re.I)
        if len(dung_sai) == 4:
            return "".join("D" if re.match(r"D[uú]ng|Đ[uú]ng", w, re.I) else "S" for w in dung_sai)

    # Phần III: số hoặc chuỗi ngắn
    if section == 3 and re.search(r"\d", v) and len(v) <= 20:
        return v

    # Generic fallback (đáp án ngắn không rõ section)
    if len(v) <= 10:
        return v

    return None


def _detect_section_from_ctx(ctx: str, current: int) -> int:
    """Detect section từ đoạn context xung quanh bảng/câu."""
    ctx_lower = ctx.lower()
    if re.search(r"ph[aầ]n\s*iii|phan\s*3|section\s*3", ctx_lower):
        return 3
    if re.search(r"ph[aầ]n\s*ii(?!i)|phan\s*2|section\s*2", ctx_lower):
        return 2
    if re.search(r"ph[aầ]n\s*i(?!i|v)|phan\s*1|section\s*1", ctx_lower):
        return 1
    return current


def parse_answer_table(answer_raw: str) -> dict[tuple[int, int], str]:
    """
    Parse bảng đáp án → {(section, q_num): answer_str}.

    Hỗ trợ nhiều format:
      - Standard: row = Câu, col = Đáp án / mã đề
      - Transposed: row = mã đề, col = câu
      - 3-col: mã đề | câu | đáp án
      - Numeric header: header = 1 2 3 4 5 ... (không có chữ "Câu")
      - Sub-item: header = 1a 1b 1c 1d 2a 2b ... (Phần II đúng/sai)
      - Nhiều bảng riêng (Phần I, II, III riêng biệt)
      - Bảng đáp án inline trong text (không phải HTML)
    """
    result: dict[tuple[int, int], str] = {}
    if not answer_raw.strip():
        return result

    # ── Parse HTML tables ──────────────────────────────────────────────────
    table_iter = list(re.finditer(r"<table[\s\S]+?</table>", answer_raw, re.I))
    current_section = 1

    for tbl_match in table_iter:
        tbl_start = tbl_match.start()
        tbl_html = tbl_match.group(0)

        # Detect section từ context trước bảng
        ctx_before = answer_raw[max(0, tbl_start - 300): tbl_start]
        current_section = _detect_section_from_ctx(ctx_before, current_section)

        rows = re.findall(r"<tr[\s\S]*?</tr>", tbl_html, re.I)
        if not rows:
            continue

        header_cells = _get_cells(rows[0])
        if not header_cells:
            continue

        h0 = header_cells[0].lower().strip()

        # ── Format: Sub-item header (1a 1b 1c 2a 2b ...) → Phần II ──────────
        if _is_subitem_header(header_cells[:8]):
            _parse_subitem_table(rows, header_cells, result)
            continue

        # ── Format: Sub-item columns (Câu | a | b | c | d) → Phần II ──────────
        is_subitem_cols = (
            re.search(r"c[aâ][uư]|cau", h0, re.I)
            and len(header_cells) >= 5
            and [c.strip().lower() for c in header_cells[1:5]] == ['a', 'b', 'c', 'd']
        )
        if is_subitem_cols:
            _parse_subitem_cols_table(rows[1:], header_cells, result)
            continue

        # ── Format: Numeric header (1 2 3 4 ... 18) → Phần I ────────────────
        if _is_numeric_header(header_cells[:8]):
            _parse_numeric_header_table(rows, header_cells, current_section, result)
            continue

        # ── Format: row = mã đề, col = câu (transposed) ─────────────────────
        is_transposed = (
            # Dạng cũ: Mã đề | 1 | 2 | ...
            (
                re.search(r"m[aă][^a-z]{0,4}[dđ]|ma\s*de", h0, re.I)
                and len(header_cells) > 2
                and re.search(r"^\d+$", re.sub(r"\s+", "", header_cells[1]))
            )
            # Dạng mới: Câu | 1 | 2 | 3 | 4 ...
            or (
                (re.search(r"c[aâ][uư]|cau|m[aă][^a-z]{0,4}[dđ]|ma\s*de", h0, re.I) or not h0)
                and len(header_cells) > 4
                and _is_numeric_header(header_cells[1:9])
            )
        )

        # ── Format: 3 cột: mã đề | câu | đáp án ─────────────────────────────
        is_three_col = (
            len(header_cells) == 3
            and re.search(r"m[aă][^a-z]{0,4}[dđ]|ma\s*de", h0, re.I)
            and re.search(r"c[aâ][uư]", header_cells[1], re.I)
        )

        # ── Format: row = câu, col = đáp án ──────────────────────────────────
        is_cau_row = re.search(r"c[aâ][uư]|cau", h0, re.I)

        if is_three_col:
            _parse_3col(rows[1:], current_section, result)
        elif is_transposed:
            _parse_transposed(rows[1:], header_cells, current_section, result)
        elif is_cau_row:
            _parse_cau_rows(rows[1:], header_cells, current_section, result)
        else:
            _parse_generic(rows[1:], current_section, result)

    # ── Parse text-based answer keys (không có HTML table) ─────────────────
    if not result:
        _parse_text_answers(answer_raw, result)

    return result


def _parse_numeric_header_table(
    rows: list[str], headers: list[str], section: int, result: dict
) -> None:
    """
    Bảng dạng:
      Header: | 1 | 2 | 3 | ... | 18 |
      Data:   | B | D | A | ... | D  |
    Mỗi cột header là số câu, data row là đáp án.
    Hỗ trợ bảng nhiều dòng data (nhiều mã đề) — lấy dòng đầu tiên.
    """
    # Build column map: col_index → q_num
    q_cols: list[tuple[int, int]] = []
    for j, h in enumerate(headers):
        m = re.fullmatch(r"(\d+)", h.strip())
        if m:
            q_cols.append((j, int(m.group(1))))

    if not q_cols:
        return

    # Lấy data từ row thứ nhất (đáp án của mã đề đầu tiên)
    for row_html in rows:
        cells = _get_cells(row_html)
        if not cells:
            continue
        # Skip nếu row toàn số (có thể là header lặp)
        if all(re.fullmatch(r"\d+", c.strip()) for c in cells if c.strip()):
            continue
        for col_i, q_n in q_cols:
            if col_i >= len(cells):
                continue
            ans = _clean_answer(cells[col_i], section)
            if ans and (section, q_n) not in result:
                result[(section, q_n)] = ans
        break  # Chỉ lấy mã đề đầu tiên


def _parse_subitem_table(rows: list[str], headers: list[str], result: dict) -> None:
    """
    Bảng Phần II đúng/sai dạng:
      Header: | 1a | 1b | 1c | 1d | 2a | 2b | 2c | 2d | ...
      Data:   |  S |  D |  D |  D |  D |  S |  D |  S | ...

    Kết quả: (2, 1) → "SDDD", (2, 2) → "DSDS", ...
    """
    section = 2
    # Parse headers: "1a" → (q_num=1, sub='a')
    col_map: list[tuple[int, int, str]] = []  # (col_idx, q_num, sub_letter)
    for j, h in enumerate(headers):
        m = re.fullmatch(r"(\d+)([abcdABCD])", h.strip())
        if m:
            col_map.append((j, int(m.group(1)), m.group(2).lower()))

    if not col_map:
        return

    # Lấy dòng data đầu tiên
    for row_html in rows:
        cells = _get_cells(row_html)
        if not cells:
            continue
        if all(re.fullmatch(r"\d+[abcd]?", c.strip(), re.I) for c in cells if c.strip()):
            continue  # Skip nếu row là header lặp

        # Group by q_num
        q_subs: dict[int, dict[str, str]] = {}
        for col_i, q_num, sub in col_map:
            if col_i >= len(cells):
                continue
            val = cells[col_i].strip().upper()
            # Normalize: S/SAI → S, D/DUNG/ĐÚNG → D
            if re.match(r"S(AI)?", val, re.I):
                val = "S"
            elif re.match(r"D(UNG)?|Đ(UNG)?", val, re.I):
                val = "D"
            if val in ("S", "D"):
                q_subs.setdefault(q_num, {})[sub] = val

        for q_num, subs in q_subs.items():
            # Ghép theo thứ tự a b c d
            ans = "".join(subs.get(k, "?") for k in "abcd")
            if "?" not in ans:
                result[(section, q_num)] = ans
        break  # Lấy dòng data đầu tiên


def _parse_subitem_cols_table(rows: list[str], headers: list[str], result: dict) -> None:
    """
    Bảng dạng:
      Header: | Câu | a | b | c | d |
      Data:   |  1  | D | S | D | D |
              |  2  | S | D | S | S |
    """
    section = 2
    # Tìm cột của a, b, c, d
    col_map: dict[str, int] = {}
    for j, h in enumerate(headers):
        val = h.strip().lower()
        if val in ('a', 'b', 'c', 'd'):
            col_map[val] = j
            
    if len(col_map) < 4:
        return
        
    for row_html in rows:
        cells = _get_cells(row_html)
        if not cells:
            continue
        # Cột đầu tiên là số câu
        m = re.search(r"(\d+)", cells[0])
        if not m:
            continue
        q_num = int(m.group(1))
        
        # Đọc các giá trị a, b, c, d
        subs = {}
        for sub_char in ('a', 'b', 'c', 'd'):
            col_idx = col_map[sub_char]
            if col_idx < len(cells):
                val = cells[col_idx].strip().upper()
                if re.match(r"S(AI)?", val, re.I):
                    val = "S"
                elif re.match(r"D(UNG)?|Đ(UNG)?", val, re.I):
                    val = "D"
                subs[sub_char] = val
        
        ans = "".join(subs.get(k, "?") for k in "abcd")
        if "?" not in ans:
            result[(section, q_num)] = ans


def _parse_3col(data_rows, section: int, result: dict) -> None:
    """Format: MÃ ĐỀ | CÂU | ĐÁP ÁN (mỗi row = 1 câu của 1 mã đề)."""
    for row in data_rows:
        cells = _get_cells(row)
        row_text = " ".join(cells)

        # Section separator
        new_sec = _detect_section_from_ctx(row_text, 0)
        if new_sec:
            section = new_sec
            continue

        if len(cells) < 3:
            continue

        m = re.search(r"(\d+)", cells[1])
        if not m:
            continue
        q_num = int(m.group(1))
        ans = _clean_answer(cells[2], section)
        if ans:
            result[(section, q_num)] = ans


def _parse_transposed(data_rows, headers: list[str], section: int, result: dict) -> None:
    """Format: row = mã đề, col = số câu (hỗ trợ xếp chồng nhiều sub-tables)."""
    def get_q_cols(h_cells):
        q_cols = []
        for j, h in enumerate(h_cells[1:], 1):
            mc = re.search(r"(\d+)", h)
            if mc:
                q_cols.append((j, int(mc.group(1))))
        return q_cols

    current_q_cols = get_q_cols(headers)

    for row in data_rows:
        cells = _get_cells(row)
        if not cells:
            continue
        
        # Check if this row is a header row (e.g. starting with "Cau"/"Question" or containing sequential numbers)
        h0 = cells[0].lower().strip() if cells else ""
        is_header = (
            re.search(r"c[aâ][uư]|cau|[qq]uestion|[qq]uest|m[aă][^a-z]{0,4}[dđ]|ma\s*de", h0, re.I)
            or _is_numeric_header(cells[1:9])
            or _is_numeric_header(cells[:8])
        )
        if is_header:
            current_q_cols = get_q_cols(cells)
            continue

        for col_i, q_n in current_q_cols:
            if col_i >= len(cells):
                continue
            ans = _clean_answer(cells[col_i], section)
            if ans and (section, q_n) not in result:
                result[(section, q_n)] = ans


def _parse_cau_rows(data_rows, headers: list[str], section: int, result: dict) -> None:
    """
    Format: row = câu, col = đáp án.

    Hỗ trợ nhiều biến thể:
      - 2 cột: Câu | Đáp án
      - 4 cột: Câu | Đáp án | Câu | Đáp án  (2 cột song song)
      - 6 cột: tương tự với 3 cột song song
    """
    # Phân tích cấu trúc header: có bao nhiêu cặp (Câu, Đáp án)?
    pairs: list[tuple[int, int]] = []  # (col_cau, col_dapan)
    i = 0
    while i < len(headers):
        h = headers[i].lower().strip()
        if re.search(r"c[aâ][uư]|cau", h, re.I):
            # Tìm cột đáp án liền sau
            for j in range(i + 1, min(i + 3, len(headers))):
                h2 = headers[j].lower().strip()
                if re.search(r"[dđ][aáà]p\s*[aáà]n|dap\s*an|dap\.?an", h2, re.I) or (
                    # Nếu header rỗng thì mặc định là cột đáp án
                    not h2 and j == i + 1
                ):
                    pairs.append((i, j))
                    i = j + 1
                    break
            else:
                # Không tìm thấy header đáp án rõ ràng → giả sử cột kế tiếp
                if i + 1 < len(headers):
                    pairs.append((i, i + 1))
                i += 2
        else:
            i += 1

    # Fallback nếu không detect được pairs
    if not pairs:
        pairs = [(0, 1)]

    # Dùng dict lưu số câu cuối cùng của từng cặp cột (col_cau)
    last_seen: dict[int, int] = {}

    for row in data_rows:
        cells = _get_cells(row)
        row_text = " ".join(cells)

        # Section separator
        new_sec = _detect_section_from_ctx(row_text, 0)
        if new_sec:
            section = new_sec
            continue

        # Đọc tất cả cặp (câu, đáp án) trong row
        for col_cau, col_dapan in pairs:
            if col_cau >= len(cells) or col_dapan >= len(cells):
                continue

            q_num = None
            m = re.search(r"(\d+)", cells[col_cau])
            if m:
                q_num = int(m.group(1))
                last_seen[col_cau] = q_num
            elif col_cau in last_seen:
                # Interpolate số câu nếu bị khuyết (OCR error)
                q_num = last_seen[col_cau] + 1
                last_seen[col_cau] = q_num

            if q_num is None:
                continue

            ans_raw = cells[col_dapan]
            # Normalize Sai/Dung → S/D trước khi clean
            ans_raw_norm = re.sub(r"\bSai\b", "S", ans_raw, flags=re.I)
            ans_raw_norm = re.sub(r"\bD[uú]ng\b|\bĐ[uú]ng\b", "D", ans_raw_norm, flags=re.I)

            ans = _clean_answer(ans_raw_norm, section)
            if not ans:
                # Fallback: thử normalize dạng "Sai" hoặc "Dung"
                if re.match(r"S(ai)?", ans_raw.strip(), re.I):
                    ans = "S"
                elif re.match(r"D[uú]ng|Dung|Đ[uú]ng", ans_raw.strip(), re.I):
                    ans = "D"

            if ans:
                result[(section, q_num)] = ans


def _parse_generic(data_rows, section: int, result: dict) -> None:
    """Fallback: thử parse cells[0]=số, cells[1]=đáp án."""
    for row in data_rows:
        cells = _get_cells(row)
        if len(cells) < 2:
            continue
        row_text = " ".join(cells)
        new_sec = _detect_section_from_ctx(row_text, 0)
        if new_sec:
            section = new_sec
            continue
        m = re.search(r"(\d+)", cells[0])
        if not m:
            continue
        q_num = int(m.group(1))
        for candidate in cells[1:]:
            ans = _clean_answer(candidate, section)
            if ans:
                result[(section, q_num)] = ans
                break


def _parse_text_answers(text: str, result: dict) -> None:
    """
    Fallback cho bảng đáp án dạng text thuần (không HTML):
      "Câu 1: A   Câu 2: B   ..."
      "1. A  2. B  3. C  ..."
    """
    section = 1
    # Pattern: "Câu N" theo sau bởi đáp án
    for m in re.finditer(
        r"(?:[Cc][aâ][uư]?\s*)?(\d+)\s*[.:\-–]\s*([ABCDabcdDS]{1,4})\b",
        text,
    ):
        q_num = int(m.group(1))
        ans_raw = m.group(2)
        ans = _clean_answer(ans_raw, section)
        if ans and (section, q_num) not in result:
            result[(section, q_num)] = ans


# ─────────────────────────────────────────────────────────────────────────────
# SOLUTION PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_solutions(solution_raw: str) -> dict[tuple[int, int], str]:
    """
    Extract lời giải từ phần solution.
    Trả về {(section, q_num): explanation_text}.

    Chiến lược:
      - Tìm "Câu N" trong solution_raw.
      - Mỗi block giữa Câu N và Câu N+1 → explanation của câu N.
      - Track section từ context (Phần I/II/III headers).
    """
    result: dict[tuple[int, int], str] = {}
    if not solution_raw.strip():
        return result

    current_section = 1
    cau_matches = list(_CAU_PAT.finditer(solution_raw))

    for i, m in enumerate(cau_matches):
        q_num = int(m.group(1) or m.group(2))
        start = m.end()
        end = cau_matches[i + 1].start() if i + 1 < len(cau_matches) else len(solution_raw)
        block = solution_raw[start:end].strip()

        # Detect section từ context trước câu hiện tại
        ctx = solution_raw[max(0, m.start() - 400): m.start()]
        current_section = _detect_section_from_ctx(ctx, current_section)

        if block:
            key = (current_section, q_num)
            if key not in result:  # Chỉ lấy lần đầu (tránh duplicate)
                result[key] = block

    return result


# ─────────────────────────────────────────────────────────────────────────────
# METADATA EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

_SUBJECT_MAP: list[tuple[str, str]] = [
    # VAT LI: chuẩn + OCR noise (VAT LI, VAT LÍ, VAT LÌ)
    (r"v[aậ]t\s*l[ýií]|vat\s*l[ii]|VAT\s*L[II]|VAT-LI", "LY"),
    # HOA HOC: chuẩn + OCR noise (HOA HQC = O bị nhầm Q)
    (r"ho[áa]\s*h[oọqQ]c|hoa\s*h[oq]c|HOA\s*H[OQ]C|HOA-HOC", "HOA"),
    (r"ti[eế]ng\s*anh|tieng\s*anh|english|TIENG\s*ANH", "ANH"),
    (r"l[iị]ch\s*s[uử]|lich\s*su|LICH\s*SU", "SU"),
    (r"ng[uữ]\s*v[aă]n|ngu\s*van|NGU\s*VAN", "VAN"),
    (r"[dđ]ia\s*l[ýií]|dia\s*li|DIA\s*LI", "DIA"),
    (r"sinh\s*h[oọ]c|sinh\s*hoc|SINH\s*HOC", "SINH"),
    (r"to[aáà]n|toan|TOAN", "TOAN"),
]


def extract_metadata(exam_body: str) -> dict:
    """Extract mã đề và môn thi từ header đề."""
    meta = {"ma_de": "01", "subject": "UNKNOWN"}

    # Mã đề: "Mã đề 1201" / "Ma de 0301" / "Mã đề thi: 123"
    m = re.search(
        r"[Mm][aà]\s*[dđ][eé]\s*(?:thi\s*:?\s*)?[:\s]*(\d{3,4})",
        exam_body[:3000],
    )
    if m:
        meta["ma_de"] = m.group(1)

    # Môn thi: scan 3000 ký tự đầu (header thường ở đây)
    # Ưu tiên tìm "Mon thi: HOA HOC" / "môn: Vật Lý" dạng explicit
    header = exam_body[:3000]
    
    # Tìm explicit "Mon thi: X" trước
    mon_match = re.search(
        r"[Mm][oô]n\s*(?:thi|h[oọ]c)?\s*[:\-–]?\s*([^\n]{3,40})",
        header,
    )
    if mon_match:
        mon_text = mon_match.group(1).strip()
        for pattern, subject in _SUBJECT_MAP:
            if re.search(pattern, mon_text, re.I):
                meta["subject"] = subject
                break

    # Fallback: scan toàn bộ header
    if meta["subject"] == "UNKNOWN":
        for pattern, subject in _SUBJECT_MAP:
            if re.search(pattern, header, re.I):
                meta["subject"] = subject
                break

    return meta


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def parse_exam_file(raw_markdown: str) -> list[ParsedExam]:
    """
    Parse 1 file markdown → list[ParsedExam].

    Xử lý được:
      - File chứa 1 đề thi
      - File chứa nhiều đề thi ghép lại
      - Đề Toán / Lý / Hóa / Anh (bất kỳ môn nào)
      - Số câu bất kỳ (không giả định 12/22/28 câu)
      - Format đáp án: HTML table, text, nhiều bảng
    """
    # Bước 0: Split nếu file chứa nhiều đề
    exam_texts = split_multi_exam(raw_markdown)

    results: list[ParsedExam] = []
    for exam_text in exam_texts:
        parsed = _parse_single_exam(exam_text)
        results.extend(parsed)

    return results


def _parse_single_exam(exam_text: str) -> list[ParsedExam]:
    """Parse 1 đề thi hoàn chỉnh."""

    # L1: Tách 3 phần
    exam_body, answer_block, solution_raw = split_document(exam_text)

    if not exam_body.strip():
        return []

    # Extract metadata
    meta = extract_metadata(exam_body)
    exam = ParsedExam(
        ma_de=meta["ma_de"],
        subject=meta["subject"],
        raw_answer_block=answer_block,
        raw_solution=solution_raw,
    )

    # L2: Detect sections + questions
    sections = detect_sections(exam_body)
    all_questions: list[dict] = []

    for sec_num, sec_text in sorted(sections.items()):
        qs = detect_questions(sec_text, sec_num)
        all_questions.extend(qs)

    # Bỏ duplicate (cùng index + section, giữ cái có raw dài hơn)
    dedup: dict[tuple[int, int], dict] = {}
    for q in all_questions:
        key = (q["section"], q["index"])
        if key not in dedup or len(q["raw"]) > len(dedup[key]["raw"]):
            dedup[key] = q
    all_questions = [dedup[k] for k in sorted(dedup.keys())]

    # L3: Classify + parse content
    for q in all_questions:
        classify_and_parse(q)

    # Parse bảng đáp án (kết hợp answer_block + đầu solution)
    ans_search_text = answer_block + "\n" + solution_raw[:4000]
    answers = parse_answer_table(ans_search_text)

    # Parse lời giải
    solutions = parse_solutions(solution_raw)

    # Merge answers + solutions → questions
    # Heuristic normalization: nếu số câu vượt quá section boundary,
    # tự điều chỉnh (ví dụ bảng dùng số liên tục 1-22 thay vì per-section)
    _normalize_answer_keys(answers, all_questions)

    for q in all_questions:
        key = (q["section"], q["index"])
        if key in answers:
            q["correct_answer"] = answers[key]
        if key in solutions:
            q["explanation"] = solutions[key]

    # Convert sang RawQuestion objects
    for q in all_questions:
        exam.questions.append(RawQuestion(
            index=q["index"],
            section=q["section"],
            q_type=q["q_type"],
            raw_text=q["raw"],
            question_text=q["question_text"],
            options=q.get("options"),
            correct_answer=q.get("correct_answer"),
            explanation=q.get("explanation"),
            image_paths=q.get("image_paths", []),
        ))

    return [exam]


def _normalize_answer_keys(
    answers: dict[tuple[int, int], str],
    questions: list[dict],
) -> None:
    """
    Một số bảng đáp án dùng số câu liên tục (1-28) thay vì per-section.
    Hàm này detect và remap nếu cần.

    Ví dụ:
      Đề có P1: câu 1-18, P2: câu 1-4, P3: câu 1-6
      Nhưng bảng đáp án có: câu 1-28 (liên tục)
      → Remap: câu 19-22 → (2, 1-4), câu 23-28 → (3, 1-6)
    """
    if not answers or not questions:
        return

    # Nhóm câu hỏi theo section
    sec_q: dict[int, list[int]] = {}
    for q in questions:
        sec_q.setdefault(q["section"], []).append(q["index"])
    for v in sec_q.values():
        v.sort()

    # Nếu tất cả đáp án đều ở section 1 nhưng số câu > max(P1)
    p1_max = max(sec_q.get(1, [0]))
    ans_max = max((k[1] for k in answers if k[0] == 1), default=0)

    if ans_max <= p1_max:
        return  # Không cần normalize

    # Xây dựng mapping: số liên tục → (section, q_num)
    cumulative: list[tuple[int, int]] = []
    for sec in sorted(sec_q.keys()):
        for q_idx in sec_q[sec]:
            cumulative.append((sec, q_idx))

    # Remap
    keys_to_remap = [(1, n) for n in range(p1_max + 1, ans_max + 1) if (1, n) in answers]
    for old_key in keys_to_remap:
        linear_idx = old_key[1] - 1  # 0-based
        if linear_idx < len(cumulative):
            new_key = cumulative[linear_idx]
            if new_key not in answers:
                answers[new_key] = answers.pop(old_key)
