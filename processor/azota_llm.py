"""
processor/azota_llm.py — Bước DeepSeek (deepseek-chat, rẻ nhất) cho pipeline Azota.

Hai việc:
  1. extract_answers()       — đọc BẢNG ĐÁP ÁN (mọi layout) + KHỚP MÃ ĐỀ → đáp án đúng.
  2. enrich_topics_levels()  — phân loại chủ đề + mức độ cho từng câu (batch 1 call/đề).

Tất cả gọi tối thiểu (1 call/việc/đề) để rẻ. Có fallback deterministic khi tắt LLM / lỗi /
thiếu API key, nên pipeline vẫn chạy được mà không cần DeepSeek.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

import config

logger = logging.getLogger(__name__)

# code môn → key trong config.TOPICS và subject_id cho fallback keyword
_CODE_TO_TOPIC_KEY = {
    "TOAN": "toan", "LY": "vat_ly", "HOA": "hoa_hoc", "SINH": "sinh_hoc",
    "SU": "lich_su", "DIA": "dia_ly", "ANH": "tieng_anh", "GDCD": "gdcd", "VAN": "ngu_van",
}
_CODE_TO_SUBJECT_ID = {"TOAN": 1, "LY": 2, "HOA": 3, "SINH": 4, "VAN": 5,
                       "SU": 6, "DIA": 7, "GDCD": 8, "ANH": 9}

_SECTION_KEY = {1: "part_1", 2: "part_2", 3: "part_3"}
_LEVELS = ["Nhận biết", "Thông hiểu", "Vận dụng", "Vận dụng cao"]


def _client():
    """Tạo sync client DeepSeek; None nếu chưa cấu hình API key."""
    if not config.DEEPSEEK_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)
    except Exception as e:
        logger.warning(f"Không tạo được DeepSeek client: {e}")
        return None


def _parse_json(raw: str) -> Optional[dict]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 1. TRÍCH ĐÁP ÁN TỪ BẢNG + KHỚP MÃ ĐỀ
# ═══════════════════════════════════════════════════════════════════════════════

_ANSWER_SYSTEM = """\
Bạn là trợ lý trích xuất BẢNG ĐÁP ÁN đề thi THPT Việt Nam.
Đầu vào là phần đáp án (có thể chứa nhiều mã đề). Nhiệm vụ: trả về đáp án ĐÚNG cho RIÊNG mã đề được chỉ định.

Trả về DUY NHẤT một JSON object:
{
  "part_1": {"1": "A", "2": "B", ...},        // trắc nghiệm: 1 chữ A/B/C/D
  "part_2": {"1": "DSDS", "2": "DDSS", ...},   // đúng/sai: 4 ký tự D(đúng)/S(sai) theo thứ tự a,b,c,d
  "part_3": {"1": "6", "2": "4200", ...}       // trả lời ngắn: số/chuỗi ngắn
}
Quy tắc:
- CHỈ lấy cột/dòng ứng với mã đề được yêu cầu. Bỏ qua các mã đề khác.
- Nếu bảng không chia phần, đặt tất cả vào "part_1".
- Không bịa đáp án cho câu không có trong bảng. Không giải thích."""


def extract_answers(
    raw_answer_block: str,
    ma_de: str,
    use_llm: bool = True,
) -> dict[tuple[int, int], str]:
    """
    Trả {(section, q_num): answer} từ bảng đáp án, khớp mã đề.
    Ưu tiên DeepSeek; fallback regex khi tắt LLM / lỗi.
    """
    if not raw_answer_block.strip():
        return {}

    if use_llm:
        client = _client()
        if client is not None:
            try:
                resp = client.chat.completions.create(
                    model=config.AZOTA_LLM_MODEL,
                    temperature=0,
                    max_tokens=2048,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": _ANSWER_SYSTEM},
                        {"role": "user", "content":
                            f"Mã đề cần lấy: {ma_de}\n\nPhần đáp án:\n{raw_answer_block}"},
                    ],
                )
                parsed = _parse_json(resp.choices[0].message.content)
                if parsed:
                    out = _json_to_answers(parsed)
                    if out:
                        return out
            except Exception as e:
                logger.warning(f"DeepSeek extract_answers lỗi: {e} — dùng fallback regex")

    return _fallback_answers(raw_answer_block, ma_de)


def _norm_answer(ans: str, sec: int) -> str:
    """Chuẩn hóa: P1/P2 viết hoa + Đ→D (đúng/sai dùng D/S); P3 giữ nguyên (có đơn vị)."""
    ans = str(ans).strip()
    if sec == 3:
        return ans
    ans = ans.upper().replace("Đ", "D").replace("Ð", "D")
    return ans


def _json_to_answers(parsed: dict) -> dict[tuple[int, int], str]:
    out: dict[tuple[int, int], str] = {}
    for sec, key in _SECTION_KEY.items():
        block = parsed.get(key) or {}
        if isinstance(block, dict):
            for q, ans in block.items():
                qn = re.search(r"\d+", str(q))
                if qn and ans:
                    out[(sec, int(qn.group()))] = _norm_answer(ans, sec)
    return out


def _fallback_answers(raw: str, ma_de: str) -> dict[tuple[int, int], str]:
    """
    Fallback regex: xử lý bảng transposed 'Mã đề | 1 | 2 | 3 / 0201 | A | A | A'
    (lấy đúng dòng mã đề) và dạng 'Câu 1: A' / '1.A'. Mặc định gán part_1.
    """
    result: dict[tuple[int, int], str] = {}
    lines = [l for l in raw.splitlines() if l.strip()]

    # Dạng bảng pipe: tìm header số câu + dòng mã đề
    header: Optional[list[str]] = None
    for line in lines:
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        nums = [c for c in cells[1:] if c.isdigit()]
        first = cells[0].lower()
        if len(nums) >= 2 and ("đề" in first or "câu" in first or first == "" or "ma de" in first):
            header = cells
            continue
        if header and re.sub(r"\s", "", cells[0]) == re.sub(r"\s", "", ma_de):
            for j, h in enumerate(header):
                if j == 0 or j >= len(cells):
                    continue
                if h.isdigit():
                    ans = cells[j].strip().upper()
                    if ans:
                        result[(1, int(h))] = ans
            break

    if result:
        return result

    # Dạng text: 'Câu 1: A', '1. A', '1.A'
    for m in re.finditer(r"(?:C[âa]u\s*)?(\d+)\s*[.:\-]\s*([ABCD]|[DS]{4}|\d[\d.,/]*)", raw, re.I):
        q = int(m.group(1))
        ans = m.group(2).strip().upper()
        result.setdefault((1, q), ans)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PHÂN LOẠI CHỦ ĐỀ + MỨC ĐỘ (batch 1 call/đề)
# ═══════════════════════════════════════════════════════════════════════════════

_ENRICH_SYSTEM = """\
Bạn là chuyên gia phân loại câu hỏi thi THPT. Với mỗi câu, xác định:
- "topic": chủ đề (CHỌN TRONG danh sách cho sẵn; nếu không khớp, chọn gần nhất)
- "level": một trong "Nhận biết" | "Thông hiểu" | "Vận dụng" | "Vận dụng cao"

Trả về DUY NHẤT một JSON object map từ số thứ tự câu sang phân loại:
{"1": {"topic": "...", "level": "..."}, "2": {...}, ...}
Không giải thích, không thêm gì khác."""


def enrich_topics_levels(questions, subject_code: str, use_llm: bool = True) -> None:
    """Điền q.level (nếu trống) và gán q.topic_name (attribute động) cho từng câu."""
    if not questions:
        return

    topic_list = config.TOPICS.get(_CODE_TO_TOPIC_KEY.get(subject_code, ""), [])

    if use_llm:
        client = _client()
        if client is not None:
            try:
                lines = []
                for i, q in enumerate(questions, 1):
                    stem = re.sub(r"!\[\]\([^)]*\)", "[hình]", q.question_text)[:300]
                    lines.append(f"{i}. {stem}")
                user = (
                    f"Môn: {subject_code}. Danh sách chủ đề cho phép: {topic_list}\n\n"
                    f"Các câu hỏi:\n" + "\n".join(lines)
                )
                resp = client.chat.completions.create(
                    model=config.AZOTA_LLM_MODEL,
                    temperature=0,
                    max_tokens=4096,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": _ENRICH_SYSTEM},
                        {"role": "user", "content": user},
                    ],
                )
                parsed = _parse_json(resp.choices[0].message.content)
                if parsed:
                    for i, q in enumerate(questions, 1):
                        info = parsed.get(str(i)) or {}
                        topic = (info.get("topic") or "").strip()
                        level = (info.get("level") or "").strip()
                        setattr(q, "topic_name", topic or _fallback_topic(subject_code, q.question_text))
                        if not q.level and level in _LEVELS:
                            q.level = level
                    _fill_defaults(questions, subject_code)
                    return
            except Exception as e:
                logger.warning(f"DeepSeek enrich lỗi: {e} — dùng fallback keyword")

    # Fallback deterministic
    for q in questions:
        setattr(q, "topic_name", _fallback_topic(subject_code, q.question_text))
    _fill_defaults(questions, subject_code)


def _fill_defaults(questions, subject_code: str) -> None:
    for q in questions:
        if not getattr(q, "topic_name", None):
            setattr(q, "topic_name", _fallback_topic(subject_code, q.question_text))
        if not q.level:
            q.level = "Thông hiểu"


def _fallback_topic(subject_code: str, text: str) -> str:
    """Keyword-based fallback (reuse _detect_topic của import_exam_deepseek)."""
    try:
        from import_exam_deepseek import _detect_topic
        sid = _CODE_TO_SUBJECT_ID.get(subject_code, 0)
        return _detect_topic(sid, text)
    except Exception:
        return "Chủ đề chung"
