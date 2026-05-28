"""
parser_v2.py — Parser chuẩn cho đề thi THPT Toán 2026.

Cấu trúc đề:
  PHẦN I  : 12 câu trắc nghiệm (chọn 1 trong A/B/C/D)
  PHẦN II : 4 câu đúng/sai (mỗi câu 4 ý a/b/c/d → D hoặc S)
  PHẦN III: 6 câu tự luận (kết quả số)

Bảng đáp án cuối đề chứa đáp án cho nhiều mã đề.
Mã đề được đọc từ header: "Mã đề thi: 1201" → dùng cột "01".
"""
import re
from dataclasses import dataclass, field
from typing import Optional

IMAGE_PUBLIC_BASE = "/exam-images"


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class ParsedQuestion:
    number: int
    content: str                    # nội dung câu hỏi (markdown, có LaTeX, có ![](…))
    question_type: str              # trac_nghiem | dung_sai | tu_luan
    options: Optional[dict]         # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer: Optional[str]   # "A"/"B"/"C"/"D" | "DSDD" | số (str)
    has_formula: bool
    has_image: bool
    has_table: bool
    section: int                    # 1/2/3


@dataclass
class ParsedExam:
    ma_de: str                      # ví dụ "1201"
    questions: list = field(default_factory=list)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_ans_boundary(text: str) -> int:
    """Find where the answer table section starts. Returns position or len(text)."""
    candidates = []

    # ĐÁP ÁN heading — phải ở đầu dòng, không phải inline "**Đáp án: 1.86**"
    # Hỗ trợ: "ĐÁP ÁN", "# ĐÁP ÁN", "## ĐÁP ÁN", "**ĐÁP ÁN**", "Đáp án"
    m = re.search(
        r'(?:^|\n)\s*(?:\*{0,2})?(?:#{1,3}\s*)?[ĐD][ÁAÀÁáa][Pp]\s*[ÁAÁáa][Nn]\s*(?:\n|$|(?!:))',
        text, re.I | re.MULTILINE
    )
    if m:
        candidates.append(m.start())

    # PHN I: (with colon = answer table section header, distinct from PHN I. in body)
    m = re.search(r'(?:^|\n)PH[A-Za-zÀ-ÿ]*N\s+I\s*:', text, re.I | re.MULTILINE)
    if m:
        candidates.append(m.start())

    # HẾT / HT end-of-exam marker
    m = re.search(r'-{2,}\s*H[ẾE]T\s*-{2,}|---+\s*HT\s*---+', text, re.I)
    if m:
        candidates.append(m.start())

    # Last <table> whose first/second cell contains "Câu" (answer table structure)
    for tm in reversed(list(re.finditer(r'<table[\s\S]*?</table>', text, re.I))):
        hcells = re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', tm.group(0)[:400], re.I)
        vals = [re.sub(r'<[^>]+>', '', c).strip() for c in hcells]
        # Answer table: "Câu" in first OR second header cell
        has_cau = (
            (vals and re.search(r'[Cc][aâ][uư]', vals[0])) or
            (len(vals) >= 2 and re.search(r'[Cc][aâ][uư]', vals[1]))
        )
        if has_cau:
            candidates.append(tm.start())
            break

    return min(candidates) if candidates else len(text)


def _has_formula(text: str) -> bool:
    return bool(re.search(r'\$[^$\n]+\$|\$\$[\s\S]+?\$\$', text))

def _has_image(text: str) -> bool:
    return bool(re.search(r'!\[.*?\]\(.*?\)', text))

def _has_table(text: str) -> bool:
    return bool(re.search(r'<table', text, re.I)) or ("| " in text and "\n|" in text)

def _fix_image_paths(text: str) -> str:
    """Chuyển images/hash.jpg → /exam-images/hash.jpg"""
    return re.sub(
        r'!\[([^\]]*)\]\(images/([^)]+)\)',
        lambda m: f'![{m.group(1)}]({IMAGE_PUBLIC_BASE}/{m.group(2)})',
        text
    )

def _normalize(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n\s*[-–]\s*\d+\s*[-–]\s*\n', '\n', text)
    text = re.sub(r'\nTrang \d+/\d+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ─── Section splitter ─────────────────────────────────────────────────────────

def _split_p2_p3_block(text: str) -> tuple:
    """Split a combined PHN II block into (p2_text, p3_text).

    đúng/sai questions have a)/b)/c)/d) subparts; tự luận don't.
    Walk questions in order; the first one without subparts starts section III.
    """
    cau_pat = re.compile(
        r'(?:^|\n)\s*[Cc][aâ][uư]?\s*(\d+)\s*[.:\s]\s*',
        re.MULTILINE
    )
    matches = list(cau_pat.finditer(text))
    first_p3_start = len(text)

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        has_subparts = bool(re.search(
            r'(?:^|\n)\s*[abcd][.)]\s', block,
            re.IGNORECASE | re.MULTILINE
        ))
        if not has_subparts:
            first_p3_start = m.start()
            break

    p2_text = text[:first_p3_start].strip()
    p3_text = text[first_p3_start:].strip()
    return p2_text, p3_text


def _split_sections(text: str) -> dict:
    """
    Tách markdown thành 3 phần đề thi THPT Toán.

    Strategy: tìm headers "## PHN ..." (bắt buộc có ## để tránh false positive)
    rồi phân loại theo context:
      - Phần I : context chứa "phuong an" / "mot phuong" / "chon mot"
      - Phần II: context chứa "dung hoac sai" / "đúng hoặc sai" / "Π"
      - Phần III: phần còn lại (sau II), KHÔNG chứa "dung hoac sai"
    Nếu không có header PHN III → tự tách block PHN II thành II + III.
    """
    # Ngừng trước bảng đáp án
    ans_pos = _find_ans_boundary(text)
    text_no_ans = text[:ans_pos]

    # Tìm section headers tại đầu dòng; dùng III|II|I|Π để tránh false-positive
    # như "phân vị" ('v' không phải mã phần hợp lệ)
    phan_pat = re.compile(
        r'(?:^|\n)\s*(?:#{1,3}\s+)?(?:PH[À-ɏḀ-ỿ]?N|PHN)\s*(?:III|II|IV|I|Π|\d{1,2})\b[^\n]*',
        re.IGNORECASE
    )
    all_matches = list(phan_pat.finditer(text_no_ans))
    if not all_matches:
        return {}

    def get_block(m_idx):
        start = all_matches[m_idx].end()
        end = all_matches[m_idx + 1].start() if m_idx + 1 < len(all_matches) else len(text_no_ans)
        return text_no_ans[start:end].strip()

    def header_line(m):
        return m.group(0).lower()

    # Classify each match
    p1_idx = p2_idx = p3_idx = None
    for i, m in enumerate(all_matches):
        h = header_line(m)
        block = get_block(i)
        has_phuong_an = bool(re.search(r'ph[uư][oơ]ng\s*[aá]n|ch[oọ]n\s*m[oộ]t', h + block[:200], re.I))
        # Allow "đúng sai" with or without "hoặc" between them
        has_dung_sai = bool(re.search(r'[dđ][úu]ng.{0,15}sai|Π', h, re.I))

        if has_phuong_an and p1_idx is None:
            p1_idx = i
        elif has_dung_sai and p2_idx is None:
            p2_idx = i
        elif p3_idx is None and i > 0 and not has_phuong_an and not has_dung_sai:
            p3_idx = i

    # Fallback: nếu không classify được bằng context, dùng thứ tự
    if p1_idx is None and len(all_matches) >= 1:
        p1_idx = 0
    if p2_idx is None and len(all_matches) >= 2:
        p2_idx = 1
    if p3_idx is None and len(all_matches) >= 3:
        p3_idx = 2

    sections = {}
    if p1_idx is not None:
        sections[1] = get_block(p1_idx)
    if p2_idx is not None:
        sections[2] = get_block(p2_idx)
    if p3_idx is not None:
        sections[3] = get_block(p3_idx)

    # Nếu không tìm thấy header PHN III → tự tách block PHN II
    if p2_idx is not None and p3_idx is None and 2 in sections:
        p2_text, p3_text = _split_p2_p3_block(sections[2])
        sections[2] = p2_text
        if p3_text:
            sections[3] = p3_text

    return sections


# ─── Answer table parser ──────────────────────────────────────────────────────

def _parse_answer_table(text: str, ma_de_col: str) -> dict:
    """
    Tìm bảng đáp án cuối đề, extract đáp án cho mã đề ma_de_col.
    Trả về:
      {
        "p1": {1: "C", 2: "D", ...},   # Phần I
        "p2": {1: "DSDD", ...},         # Phần II
        "p3": {1: "100", 2: "3.93",...} # Phần III
      }
    """
    ans_pos = _find_ans_boundary(text)
    if ans_pos >= len(text):
        return {}
    ans_text = text[ans_pos:]

    # Tìm bảng HTML <table>
    table_match = re.search(r'<table[\s\S]+?</table>', ans_text, re.I)
    if not table_match:
        return {}

    table_html = table_match.group(0)
    rows = re.findall(r'<tr[\s\S]*?</tr>', table_html, re.I)
    if not rows:
        return {}

    # Parse header row → detect format and find mã đề column
    header_cells = re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', rows[0], re.I)
    header_vals = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]

    # Detect transposed format: header[0]="Mã đề" and header[1+] are question numbers
    # Question numbers have no leading zeros (e.g. "1","2"); mã đề values do ("01","1201")
    is_transposed = (
        bool(header_vals) and
        re.search(r'm[aăā][^a-z]{0,3}[dđ]', header_vals[0], re.I) and
        header_vals[1:] and
        re.match(r'^[1-9]\d?$', re.sub(r'\s+', '', header_vals[1]))
    )

    # 3-column format: MÃ ĐỀ | CÂU | ĐÁP ÁN (mỗi row là 1 câu của 1 mã đề)
    is_three_col = (
        len(header_vals) == 3 and
        re.search(r'm[aă][^a-z]{0,5}[dđ]', header_vals[0], re.I) and
        re.search(r'[Cc][aâ][uư]', header_vals[1], re.I)
    )

    if is_three_col:
        short = ma_de_col.lstrip('0') or '0'
        p1, p2, p3 = {}, {}, {}
        current_section = 1
        for row in rows[1:]:
            cells = re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', row, re.I)
            vals = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            row_text = ' '.join(vals)
            # Section separator row (colspan): "PHẦN I", "PHẦN II", "PHẦN III"
            if re.search(r'III', row_text, re.I):
                current_section = 3; continue
            elif re.search(r'II', row_text, re.I) and not re.search(r'III', row_text, re.I):
                current_section = 2; continue
            elif re.search(r'PH[À-ɏḀ-ỿ]?N\s*I\b', row_text, re.I):
                current_section = 1; continue
            if len(vals) < 3:
                continue
            ma = re.sub(r'\s+', '', vals[0])
            if ma != ma_de_col and ma != short and not ma.endswith(ma_de_col):
                continue
            cau_str = re.sub(r'\s+', '', vals[1])
            ans_str = re.sub(r'\s+', '', vals[2])
            if not cau_str.isdigit():
                continue
            n = int(cau_str)
            if current_section == 1 and re.fullmatch(r'[ABCD]', ans_str, re.I):
                p1[n] = ans_str.upper()
            elif current_section == 2:
                if re.fullmatch(r'[DS]{4}', ans_str, re.I):
                    p2[n] = ans_str.upper()
                elif ans_str:
                    p2[n] = ans_str.upper()
            elif current_section == 3 and ans_str:
                p3[n] = ans_str
        return {"p1": p1, "p2": p2, "p3": p3}

    if is_transposed:
        # Transposed: rows = mã đề, columns = question numbers.
        # Answer section may have MULTIPLE tables (one per section I/II/III).
        # Scan all tables, accumulate p1/p2/p3.
        short = ma_de_col.lstrip('0') or '0'
        p1, p2, p3 = {}, {}, {}

        all_tables = list(re.finditer(r'<table[\s\S]+?</table>', ans_text, re.I))
        for tm in all_tables:
            t_rows = re.findall(r'<tr[\s\S]*?</tr>', tm.group(0), re.I)
            if not t_rows:
                continue
            t_hcells = re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', t_rows[0], re.I)
            t_hvals = [re.sub(r'<[^>]+>', '', c).strip() for c in t_hcells]
            # Build column map: (col_idx → question_number)
            # Handles both plain "1" and "Câu 1" column headers
            q_cols = []
            for j, h in enumerate(t_hvals[1:], 1):
                h_c = re.sub(r'\s+', '', h)
                if re.match(r'^\d+$', h_c):
                    q_cols.append((j, int(h_c)))
                else:
                    mc = re.match(r'[Cc][aâ][uư]?(\d+)', h_c, re.I)
                    if mc:
                        q_cols.append((j, int(mc.group(1))))
            if not q_cols:
                continue
            # Find row for our mã đề
            for t_row in t_rows[1:]:
                t_cells = re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', t_row, re.I)
                t_vals = [re.sub(r'<[^>]+>', '', c).strip() for c in t_cells]
                if not t_vals:
                    continue
                row_label = re.sub(r'\s+', '', t_vals[0])
                if not (row_label == ma_de_col or row_label == short or
                        row_label.endswith(ma_de_col)):
                    continue
                for col_i, q_n in q_cols:
                    if col_i >= len(t_vals):
                        continue
                    ans_clean = re.sub(r'\s+', '', t_vals[col_i])
                    if re.fullmatch(r'[ABCD]', ans_clean, re.I):
                        p1[q_n] = ans_clean.upper()
                    elif re.fullmatch(r'[DS]{4}', ans_clean, re.I):
                        p2[q_n] = ans_clean.upper()
                    else:
                        # Verbose DS format: "a)Đ - b)S - c)S - d)S"
                        ds_letters = re.findall(r'[abcd]\)[^-]*([ĐDS])', ans_clean, re.I)
                        if len(ds_letters) == 4:
                            mp = {'Đ': 'D', 'đ': 'D', 'D': 'D', 'd': 'D', 'S': 'S', 's': 'S'}
                            p2[q_n] = ''.join(mp.get(l, l.upper()) for l in ds_letters)
                        elif ans_clean and re.search(r'\d', ans_clean):
                            p3[q_n] = ans_clean
        return {"p1": p1, "p2": p2, "p3": p3}

    # Standard format: rows = questions, columns = mã đề
    # Tìm cột khớp với ma_de_col (ví dụ "01", "1", "1201")
    col_idx = None
    short = ma_de_col.lstrip('0') or '0'
    for i, h in enumerate(header_vals[1:], 1):
        h_clean = re.sub(r'\s+', '', h)
        if h_clean == ma_de_col or h_clean == short or h_clean.endswith(ma_de_col):
            col_idx = i
            break

    if col_idx is None:
        # Fallback: dùng cột 1 (cột đáp án đầu tiên)
        col_idx = 1

    # Parse từng row
    p1, p2, p3 = {}, {}, {}

    for row in rows[1:]:
        cells = re.findall(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', row, re.I)
        if not cells:
            continue
        vals = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if len(vals) <= col_idx:
            continue

        label = vals[0].strip()
        ans_val = vals[col_idx].strip()

        # Support "Câu N" format AND plain "N" format (some answer tables)
        m_cau = re.match(r'[Cc][aâ][uư]?\s*(\d+)', label)
        if not m_cau:
            m_cau = re.match(r'^\s*(\d+)\s*$', label)
        if not m_cau:
            continue
        n = int(m_cau.group(1))

        # Phân loại theo độ dài và nội dung đáp án
        ans_clean = re.sub(r'\s+', '', ans_val)

        if re.fullmatch(r'[ABCD]', ans_clean, re.I):
            # Phần I: 1 ký tự A/B/C/D
            p1[n] = ans_clean.upper()
        elif re.fullmatch(r'[DS]{4}', ans_clean, re.I):
            # Phần II: 4 ký tự D/S
            p2[n] = ans_clean.upper()
        elif ans_clean and not re.fullmatch(r'[ABCD]', ans_clean, re.I):
            # Phần III: số hoặc chuỗi khác
            if re.search(r'\d', ans_clean):
                p3[n] = ans_clean

    # Normalize continuous numbering to section-relative (some tables use 1-12, 13-16, 17+)
    if p2 and min(p2.keys()) > 4:
        offset = max(p1.keys()) if p1 else 12
        p2 = {k - offset: v for k, v in p2.items()}
    if p3 and min(p3.keys()) > 6:
        max_p1 = max(p1.keys()) if p1 else 12
        max_p2 = max(p2.keys()) if p2 else 4
        offset = max_p1 + max_p2
        p3 = {k - offset: v for k, v in p3.items()}

    return {"p1": p1, "p2": p2, "p3": p3}


# ─── Trắc nghiệm parser (Phần I) ─────────────────────────────────────────────

def _extract_options_tracnghiem(text: str) -> tuple:
    """Tách nội dung câu và đáp án A/B/C/D. Trả về (content, options_dict|None)."""
    # Strategy 1: options trên dòng riêng "A. text" hoặc "A) text"
    newline_pat = re.compile(
        r'(?:^|\n)\s*([ABCD])[.)]\s*(.+?)(?=\n\s*[ABCD][.)]|\Z)',
        re.DOTALL | re.MULTILINE
    )
    nl_matches = list(newline_pat.finditer(text))
    if len({m.group(1).upper() for m in nl_matches}) >= 3:
        content = text[:nl_matches[0].start()].strip()
        options = {}
        for m in nl_matches:
            options[m.group(1).upper()] = re.sub(r'\s+', ' ', m.group(2)).strip()
        if len(options) >= 3:
            return content, options

    flat = ' ' + re.sub(r'\s+', ' ', text).strip() + ' '

    # Strategy 2: inline "A. text B. text C. text D. text"
    for sep in [r'[.)]', r'[.)]']:
        pat = re.compile(
            r' A' + sep + r'\s*(.+?) B' + sep + r'\s*(.+?) C' + sep + r'\s*(.+?) D' + sep + r'\s*(.+?)(?= [ABCD][.)]|\Z)',
            re.IGNORECASE
        )
        m = pat.search(flat)
        if m:
            groups = [g.strip() for g in m.groups()]
            if all(groups) and all(len(g) < 500 for g in groups):
                a_start = flat.index(m.group(0))
                return flat[:a_start].strip(), dict(zip('ABCD', groups))

    return text.strip(), None


# ─── Phần I parser ────────────────────────────────────────────────────────────

def _parse_section1(text: str, answers: dict) -> list:
    """Parse 12 câu trắc nghiệm từ Phần I."""
    cau_pat = re.compile(
        r'(?:^|\n)\s*[Cc][aâ][uư]?\s*(\d+)\s*[.:\s]\s*',
        re.MULTILINE
    )
    matches = list(cau_pat.finditer(text))
    questions = []

    for i, m in enumerate(matches):
        n = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[start:end].strip()
        if len(raw) < 5:
            continue

        content, options = _extract_options_tracnghiem(raw)
        content = _fix_image_paths(content)
        if options:
            options = {k: _fix_image_paths(v) for k, v in options.items()}

        questions.append(ParsedQuestion(
            number=n,
            content=content,
            question_type='trac_nghiem',
            options=options,
            correct_answer=answers.get(n),
            has_formula=_has_formula(raw),
            has_image=_has_image(raw),
            has_table=_has_table(raw),
            section=1,
        ))

    return questions


# ─── Phần II parser ───────────────────────────────────────────────────────────

def _parse_section2(text: str, answers: dict) -> list:
    """Parse 4 câu đúng/sai từ Phần II."""
    cau_pat = re.compile(
        r'(?:^|\n)\s*[Cc][aâ][uư]?\s*(\d+)\s*[.:\s]\s*',
        re.MULTILINE
    )
    matches = list(cau_pat.finditer(text))
    questions = []

    for i, m in enumerate(matches):
        n = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[start:end].strip()
        if len(raw) < 5:
            continue

        # Tách phần đề và các ý a/b/c/d
        sub_pat = re.compile(r'(?:^|\n)\s*([abcd])[.)]\s*(.+?)(?=\n\s*[abcd][.)]|\Z)', re.DOTALL | re.MULTILINE)
        sub_matches = list(sub_pat.finditer(raw))

        if sub_matches:
            stem = raw[:sub_matches[0].start()].strip()
            options_ds = {}
            for sm in sub_matches:
                key = sm.group(1).upper()
                val = re.sub(r'\s+', ' ', sm.group(2)).strip()
                options_ds[key] = _fix_image_paths(val)
            content = _fix_image_paths(stem)
        else:
            content = _fix_image_paths(raw)
            options_ds = None

        # Đáp án dạng "DSDD" → {"A":"Đúng","B":"Sai","C":"Đúng","D":"Đúng"}
        raw_ans = answers.get(n, '')
        correct_answer = None
        if raw_ans and len(raw_ans) == 4:
            mapping = {'D': 'Đúng', 'S': 'Sai'}
            ans_dict = {}
            for ki, letter in enumerate('ABCD'):
                ans_dict[letter] = mapping.get(raw_ans[ki].upper(), raw_ans[ki])
            correct_answer = raw_ans

        questions.append(ParsedQuestion(
            number=n,
            content=content,
            question_type='dung_sai',
            options=options_ds,
            correct_answer=correct_answer,
            has_formula=_has_formula(raw),
            has_image=_has_image(raw),
            has_table=_has_table(raw),
            section=2,
        ))

    return questions


# ─── Phần III parser ──────────────────────────────────────────────────────────

def _parse_section3(text: str, answers: dict) -> list:
    """Parse 6 câu tự luận từ Phần III."""
    cau_pat = re.compile(
        r'(?:^|\n)\s*[Cc][aâ][uư]?\s*(\d+)\s*[.:\s]\s*',
        re.MULTILINE
    )
    matches = list(cau_pat.finditer(text))
    questions = []

    for i, m in enumerate(matches):
        n = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[start:end].strip()
        if len(raw) < 5:
            continue

        content = _fix_image_paths(raw)

        questions.append(ParsedQuestion(
            number=n,
            content=content,
            question_type='tu_luan',
            options=None,
            correct_answer=answers.get(n),
            has_formula=_has_formula(raw),
            has_image=_has_image(raw),
            has_table=_has_table(raw),
            section=3,
        ))

    return questions


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_exam(markdown: str) -> ParsedExam:
    """
    Parse toàn bộ markdown của 1 đề thi.
    Tự động detect mã đề, tách 3 phần, extract đáp án.
    """
    text = _normalize(markdown)

    # Detect mã đề từ header (ví dụ "Ma dé thi: 1201" hoặc "Mã đề: 1201")
    ma_de = '01'
    ma_match = re.search(r'[Mm][aà]\s*[dđ][eé]\s*(?:thi\s*:?\s*)?[:\s]*(\d{3,4})', text)
    if ma_match:
        ma_de_full = ma_match.group(1)
        ma_de = ma_de_full[-2:]  # Lấy 2 số cuối: "1201" → "01"

    # Tách phần
    sections = _split_sections(text)

    # Parse bảng đáp án
    all_answers = _parse_answer_table(text, ma_de)
    ans_p1 = all_answers.get('p1', {})
    ans_p2 = all_answers.get('p2', {})
    ans_p3 = all_answers.get('p3', {})

    questions = []
    if 1 in sections:
        questions += _parse_section1(sections[1], ans_p1)
    if 2 in sections:
        questions += _parse_section2(sections[2], ans_p2)
    if 3 in sections:
        questions += _parse_section3(sections[3], ans_p3)

    return ParsedExam(ma_de=ma_de, questions=questions)
