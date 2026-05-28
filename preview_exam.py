"""
preview_exam.py — Chạy pipeline OCR → DeepSeek → HTML đẹp với KaTeX

Usage:
    python preview_exam.py "path/to/de_thi.pdf"
    python preview_exam.py "path/to/de_thi.pdf" --skip-ocr   # Dùng lại .md đã có
    python preview_exam.py "path/to/de_thi.pdf" --skip-norm  # Dùng lại normalized đã có

Output:
    data/processed/<tên-file>_preview.html  ← mở trong browser
"""

import argparse
import asyncio
import os
import re
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))
import config
from processor.ocr import MinerUClient

console = Console()


# ─── Step 1: OCR với MinerU ──────────────────────────────────────────────────

def run_ocr(pdf_path: Path, out_dir: Path) -> Path:
    md_path = out_dir / f"{pdf_path.stem}.md"
    if md_path.exists():
        console.print(f"[green]✓[/green] Dùng lại MinerU output: [cyan]{md_path.name}[/cyan]")
        return md_path

    console.print(f"[yellow]→[/yellow] Gọi MinerU API cho [cyan]{pdf_path.name}[/cyan]...")
    client = MinerUClient(config.MINERU_API_KEY)
    result = client.parse_pdf(
        str(pdf_path),
        save_markdown_to=str(md_path),
        image_dir=str(out_dir / "images"),
        enable_formula=True,
        enable_table=True,
        is_ocr=True,
        language="vi",
    )
    if not result:
        console.print("[red]✗ MinerU thất bại![/red]")
        sys.exit(1)
    console.print(f"[green]✓[/green] MinerU xong: {len(result['markdown']):,} ký tự, {result['page_count']} trang")
    return md_path


# ─── Step 2: Chuẩn hóa EXAM-TAG-12 bằng DeepSeek ───────────────────────────

NORMALIZE_SYSTEM = """\
Bạn là chuyên gia xử lý đề thi Toán THPT Việt Nam.
Nhiệm vụ: nhận đoạn Markdown thô từ MinerU OCR và chuẩn hóa theo bộ quy tắc EXAM-TAG-12.

QUY TẮC EXAM-TAG-12 (TUYỆT ĐỐI tuân thủ):
1. Tiêu đề 3 phần: ==PHAN 1==  ==PHAN 2==  ==PHAN 3== — mỗi cái trên dòng riêng.
2. Đầu mỗi câu hỏi: [CAU 1]  [CAU 2]  ...  [CAU N] — bắt buộc ở đầu dòng mới.
3. Đáp án trắc nghiệm (Phần I): [A].   [B].   [C].   [D].  — mỗi cái xuống dòng.
4. Ý đúng/sai (Phần II): [a].   [b].   [c].   [d].  — mỗi cái xuống dòng.
5. Nếu tìm thấy bảng đáp án cuối đề: khớp đáp án vào cuối mỗi câu dưới dạng [DAPAN: X]
   (X ví dụ: A, B, DSDD, 1.5). Đặt ngay sau nội dung câu, trước [CAU N+1].
6. GIỮ NGUYÊN 100% công thức LaTeX ($...$, $$...$$) và thẻ ảnh ![](images/...).
7. Sửa lỗi OCR (chữ dính, ký tự vỡ, thiếu dấu tiếng Việt) nhưng KHÔNG thêm/bỏ câu.
8. KHÔNG giải thích, KHÔNG thêm tiêu đề markdown khác, KHÔNG bình luận.
9. Nếu sau nội dung câu xuất hiện Lời giải / Hướng dẫn giải:
   KHÔNG tạo CAU mới, đặt toàn bộ vào: [LOIGIAI: <nội dung>]"""

CHUNK_SIZE = 10_000


async def normalize_markdown(raw: str, out_dir: Path, stem: str) -> str:
    from openai import AsyncOpenAI

    norm_path = out_dir / f"{stem}_normalized.md"
    if norm_path.exists():
        console.print(f"[green]✓[/green] Dùng lại normalized: [cyan]{norm_path.name}[/cyan]")
        return norm_path.read_text(encoding="utf-8")

    deepseek = AsyncOpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)

    paragraphs = raw.split("\n\n")
    chunks, cur = [], ""
    for para in paragraphs:
        if len(cur) + len(para) + 2 > CHUNK_SIZE and cur:
            chunks.append(cur.strip())
            cur = para
        else:
            cur = (cur + "\n\n" + para) if cur else para
    if cur:
        chunks.append(cur.strip())

    console.print(f"[yellow]→[/yellow] DeepSeek normalize: {len(chunks)} chunk(s)...")
    parts, prev_ctx = [], ""

    for i, chunk in enumerate(chunks):
        console.print(f"  Chunk {i+1}/{len(chunks)}...", end="")
        user_content = (
            f"CONTEXT (đoạn trước kết thúc ở): {prev_ctx}\n\nTiếp tục chuẩn hóa "
            f"(KHÔNG lặp lại context, tiếp nối đúng phần/số câu):\n\n{chunk}"
        ) if prev_ctx else (
            f"Chuẩn hóa đoạn markdown sau theo EXAM-TAG-12. "
            f"Chỉ trả về markdown đã chuẩn hóa:\n\n{chunk}"
        )
        try:
            resp = await deepseek.chat.completions.create(
                model="deepseek-chat",
                temperature=0,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": NORMALIZE_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
            )
            result = resp.choices[0].message.content.strip()
            parts.append(result)
            phan_m = list(re.finditer(r'==PHAN\s*(\d+)==', result, re.I))
            cau_m  = list(re.finditer(r'\[CAU\s+(\d+)\]', result, re.I))
            lp = phan_m[-1].group(0) if phan_m else ""
            lc = cau_m[-1].group(0) if cau_m else ""
            prev_ctx = f"đang ở {lp}, xong {lc}" if lp and lc else lp or lc or ""
            console.print(f" [green]OK[/green] ({len(result)} chars, {lc or 'no CAU'})")
        except Exception as e:
            parts.append(chunk)
            prev_ctx = ""
            console.print(f" [red]Lỗi: {e}[/red]")

    normalized = "\n\n".join(parts)
    norm_path.write_text(normalized, encoding="utf-8")
    console.print(f"[green]✓[/green] Normalized lưu tại [cyan]{norm_path.name}[/cyan] ({len(normalized):,} chars)")
    return normalized


# ─── Step 3: Parse câu hỏi ──────────────────────────────────────────────────

def _parse_one_question(raw: str, pnum: int, qnum: int, abs_img_dir: Path) -> dict:
    """Parse 1 câu từ raw EXAM-TAG-12 content."""
    QTYPE = {1: "trac_nghiem", 2: "dung_sai", 3: "tu_luan"}

    # Trích [DAPAN: X]
    dapan_m = re.search(r'\[DAPAN:\s*([^\]]+)\]', raw, re.I)
    correct = dapan_m.group(1).strip() if dapan_m else None

    # Trích [LOIGIAI: ...] — lookahead tránh stop sớm; fallback cho truncated (không có ])
    loigiai_m = re.search(r'\[LOIGIAI:\s*([\s\S]+?)\]\s*(?=\[DAPAN|\[CAU|==PHAN|\Z)', raw, re.I)
    if loigiai_m:
        explanation = loigiai_m.group(1).strip()
    else:
        m = re.search(r'\[LOIGIAI:\s*([\s\S]+)', raw, re.I)
        explanation = m.group(1).strip() if m else None

    # Body: xóa tags meta
    body = re.sub(r'\[DAPAN:[^\]]+\]', '', raw, flags=re.I)
    # Xóa LOIGIAI (kể cả bị truncate không có ]) — luôn là phần cuối của body
    body = re.sub(r'\[LOIGIAI:[\s\S]+', '', body, flags=re.I)
    body = re.sub(r'^\s*\[CAU\s+\d+\]\.?\s*', '', body, flags=re.I | re.M).strip()

    # Tách options [A]. / [a]. hoặc A. / a. (có hoặc không có ngoặc vuông)
    opt_pat = re.compile(r'(?:^|\n)\s*\[?([ABCDabcd])\]?\.[ \t]*', re.M)
    opt_matches = list(opt_pat.finditer(body))

    options: dict[str, str] = {}
    content = body
    if opt_matches:
        content = body[:opt_matches[0].start()].strip()
        for j, om in enumerate(opt_matches):
            key = om.group(1)  # giữ nguyên case (A/B/C/D hoặc a/b/c/d)
            val_start = om.end()
            val_end = opt_matches[j+1].start() if j+1 < len(opt_matches) else len(body)
            val = body[val_start:val_end].strip()
            val = re.sub(r'\[DAPAN:[^\]]+\]', '', val).strip()
            if val:
                options[key] = val

    # Fix image paths
    def fix_img(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        if not src.startswith("http"):
            abs_path = abs_img_dir / Path(src).name
            if abs_path.exists():
                src = abs_path.resolve().as_uri()
        return f'![{alt}]({src})'

    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', fix_img, content)
    options = {k: re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', fix_img, v) for k, v in options.items()}

    return {
        "part":        pnum,
        "qtype":       QTYPE.get(pnum, "tu_luan"),
        "num":         qnum,
        "content":     content,
        "options":     options,
        "correct":     correct,
        "explanation": explanation,
    }


_IMG_PAT     = re.compile(r'!\[[^\]]*\]\([^)]+\)')
_TRA_LOI_PAT = re.compile(r'Tr[aả]\s*l[oờ]i\s*:([\s\S]*?)(?=\[DAPAN:|\[LOIGIAI:|\[CAU\s+\d+\]|==PHAN|\Z)', re.I)
_NEEDS_IMAGE = re.compile(r'(như\s+hình\s+v[eẽ]|hình\s+v[eẽ]\s+bên|hình\s+dưới|hình\s+bên|xem\s+hình|theo\s+hình|như\s+hình)', re.I)


def parse_questions(normalized: str, image_dir: Path) -> list[dict]:
    """
    Tách EXAM-TAG-12 thành list câu hỏi.
    Xử lý trùng PHAN (do DeepSeek reset context giữa chunks):
      - Gom tất cả câu từ mọi instance của từng PHAN
      - Dedup theo số câu, giữ bản nội dung dài hơn
    Phục hồi ảnh bị mất:
      - Ảnh trong mục "Trả lời:" (answer space) của các instances bị bỏ
        được inject lại vào body nếu câu có "như hình vẽ" nhưng thiếu ảnh
    """
    abs_img_dir = image_dir.resolve()

    # Collect: pnum → {qnum: raw_content}
    collected: dict[int, dict[int, str]] = {}
    # image_bank: pnum → {qnum: list of img tags from "Trả lời:" sections}
    image_bank: dict[int, dict[int, list]] = {}

    part_pat = re.compile(r'==PHAN\s*(\d+)==', re.I)
    cau_pat  = re.compile(r'(?:^|\n)\s*\[CAU\s+(\d+)\]', re.I)

    splits = list(part_pat.finditer(normalized))
    for i, pm in enumerate(splits):
        pnum = int(pm.group(1))
        p_start = pm.end()
        p_end   = splits[i+1].start() if i+1 < len(splits) else len(normalized)
        part_text = normalized[p_start:p_end]

        cau_matches = list(cau_pat.finditer(part_text))
        if pnum not in collected:
            collected[pnum] = {}
        if pnum not in image_bank:
            image_bank[pnum] = {}

        for j, cm in enumerate(cau_matches):
            qnum   = int(cm.group(1))
            q_start = cm.start()
            q_end   = cau_matches[j+1].start() if j+1 < len(cau_matches) else len(part_text)
            raw = part_text[q_start:q_end].strip()

            # Thu thập ảnh từ mục "Trả lời:" trong bất kỳ instance nào
            tl_m = _TRA_LOI_PAT.search(raw)
            if tl_m:
                imgs = _IMG_PAT.findall(tl_m.group(1))
                if imgs:
                    if qnum not in image_bank[pnum]:
                        image_bank[pnum][qnum] = []
                    for img in imgs:
                        if img not in image_bank[pnum][qnum]:
                            image_bank[pnum][qnum].append(img)

            existing = collected[pnum].get(qnum, "")
            # Ưu tiên bản có DAPAN/LOIGIAI; nếu cùng loại thì giữ bản dài hơn
            new_score = bool(re.search(r'\[DAPAN:', raw, re.I)) * 2 + bool(re.search(r'\[LOIGIAI:', raw, re.I))
            old_score = bool(re.search(r'\[DAPAN:', existing, re.I)) * 2 + bool(re.search(r'\[LOIGIAI:', existing, re.I))
            if new_score > old_score or (new_score == old_score and len(raw) > len(existing)):
                collected[pnum][qnum] = raw

    if not collected:
        collected[1] = {1: normalized}

    # Inject ảnh bị mất vào body câu hỏi nếu:
    # 1. body đề cập "như hình vẽ" hoặc tương đương
    # 2. body chưa có ảnh nào
    # 3. image_bank có ảnh từ mục "Trả lời:" của instance bị bỏ
    for pnum in collected:
        for qnum in collected[pnum]:
            bank = image_bank.get(pnum, {}).get(qnum, [])
            if not bank:
                continue
            raw = collected[pnum][qnum]
            meta_m = re.search(r'\[DAPAN:|\[LOIGIAI:', raw, re.I)
            body_text = raw[:meta_m.start()] if meta_m else raw
            if not _NEEDS_IMAGE.search(body_text):
                continue
            if _IMG_PAT.search(body_text):
                continue  # body đã có ảnh
            inject_str = '\n'.join(bank) + '\n'
            if meta_m:
                raw = raw[:meta_m.start()] + inject_str + raw[meta_m.start():]
            else:
                raw += '\n' + inject_str
            collected[pnum][qnum] = raw

    questions = []
    for pnum in sorted(collected):
        for qnum in sorted(collected[pnum]):
            q = _parse_one_question(collected[pnum][qnum], pnum, qnum, abs_img_dir)
            questions.append(q)

    return questions


# ─── Step 4: Render HTML ─────────────────────────────────────────────────────

def escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md_to_html(text: str) -> str:
    """Convert markdown-ish text (với LaTeX) thành HTML. LaTeX giữ nguyên để KaTeX render."""
    if not text:
        return ""
    
    # Tách LaTeX để tránh thay thế \n -> <br> bên trong công thức
    math_re = re.compile(r'(\$\$[\s\S]+?\$\$|\$(?:[^$\\\n]|\\.)+?\$)')
    segments = math_re.split(text)
    
    result_parts = []
    for seg in segments:
        if (seg.startswith('$$') and seg.endsWith('$$')) or (seg.startsWith('$') and seg.endsWith('$') and len(seg) > 1):
            result_parts.append(seg)
        else:
            # Bold **...**
            s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', seg)
            # Images ![alt](src)
            s = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
                       r'<img src="\2" alt="\1" style="max-width:100%;max-height:300px;vertical-align:middle;margin:4px 0">',
                       s)
            # Newlines → <br>
            s = s.replace("\n", "<br>")
            result_parts.append(s)
            
    return "".join(result_parts)


SECTION_LABELS = {
    1: ("I", "Trắc nghiệm nhiều phương án lựa chọn", "#1e3a5f"),
    2: ("II", "Trắc nghiệm đúng/sai", "#5b21b6"),
    3: ("III", "Tự luận", "#92400e"),
}


def render_html(questions: list[dict], title: str) -> str:
    total = len(questions)
    p1 = [q for q in questions if q["part"] == 1]
    p2 = [q for q in questions if q["part"] == 2]
    p3 = [q for q in questions if q["part"] == 3]

    def render_section(qs: list[dict], pnum: int) -> str:
        if not qs:
            return ""
        roman, label, color = SECTION_LABELS.get(pnum, ("?", "", "#333"))
        rows = ""
        for q in qs:
            content_html = md_to_html(q["content"])
            opt_html = ""
            if q["options"]:
                keys = sorted(q["options"].keys())
                is_dung_sai = q["qtype"] == "dung_sai"
                is_ds_answer = (is_dung_sai and q["correct"]
                                and re.fullmatch(r'[DdSs]+', q["correct"].strip()))
                opt_rows = ""
                for k in keys:
                    if is_ds_answer:
                        pos = "abcd".find(k.lower())
                        ds_char = q["correct"][pos].upper() if 0 <= pos < len(q["correct"]) else ""
                        is_correct = ds_char == "D"
                        badge_style = ("background:#d1fae5;color:#065f46" if is_correct
                                       else "background:#fee2e2;color:#991b1b")
                        ds_badge = (f'<span style="font-size:10px;font-weight:700;'
                                    f'padding:1px 6px;border-radius:3px;margin-left:auto;'
                                    f'font-family:sans-serif;{badge_style}">{ds_char}</span>'
                                    if ds_char else "")
                    else:
                        is_correct = bool(q["correct"] and k.upper() in q["correct"].upper())
                        ds_badge = ""
                    opt_style = "background:#d1fae5;border-color:#6ee7b7;font-weight:600" if is_correct else ""
                    opt_rows += f"""
                    <div class="option" style="{opt_style}">
                      <span class="opt-key">{k}</span>
                      <span class="opt-val">{md_to_html(q["options"][k])}</span>
                      {ds_badge}
                    </div>"""
                grid = 'grid-template-columns:1fr' if is_dung_sai else ''
                opt_html = f'<div class="options" style="{grid}">{opt_rows}</div>'

            correct_badge = ""
            if q["correct"]:
                correct_badge = f'<span class="badge correct">ĐA: {escape_html(q["correct"])}</span>'

            explanation_html = ""
            if q["explanation"]:
                explanation_html = f"""
                <details class="explanation">
                  <summary>💡 Lời giải</summary>
                  <div class="explanation-body">{md_to_html(q["explanation"])}</div>
                </details>"""

            rows += f"""
            <div class="question" id="q{pnum}-{q["num"]}">
              <div class="q-header">
                <span class="q-num">Câu {q["num"]}</span>
                {correct_badge}
              </div>
              <div class="q-content">{content_html}</div>
              {opt_html}
              {explanation_html}
            </div>"""

        return f"""
        <section class="section">
          <div class="section-header" style="border-left-color:{color};color:{color}">
            <span class="section-roman">Phần {roman}</span>
            <span class="section-label">{label}</span>
            <span class="section-count">{len(qs)} câu</span>
          </div>
          <div class="questions">{rows}</div>
        </section>"""

    body = render_section(p1, 1) + render_section(p2, 2) + render_section(p3, 3)

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_html(title)}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.17.0/dist/katex.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.17.0/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.17.0/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {{
      delimiters: [
        {{left: '$$', right: '$$', display: true}},
        {{left: '$', right: '$', display: false}}
      ],
      throwOnError: false
    }});"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Times New Roman", Times, serif;
      background: #f5f5f5;
      color: #1a1a1a;
      font-size: 15px;
      line-height: 1.7;
    }}
    .page {{
      max-width: 860px;
      margin: 0 auto;
      background: white;
      padding: 40px 50px 60px;
      box-shadow: 0 2px 20px rgba(0,0,0,.08);
      min-height: 100vh;
    }}
    header {{
      text-align: center;
      border-bottom: 2px solid #1e3a5f;
      padding-bottom: 16px;
      margin-bottom: 28px;
    }}
    header h1 {{
      font-size: 18px;
      font-weight: 700;
      color: #1e3a5f;
      text-transform: uppercase;
      letter-spacing: .5px;
    }}
    header .meta {{
      font-size: 13px;
      color: #666;
      margin-top: 6px;
    }}
    .toc {{
      background: #f8f9ff;
      border: 1px solid #dde5f4;
      border-radius: 8px;
      padding: 12px 20px;
      margin-bottom: 28px;
      display: flex;
      gap: 24px;
      flex-wrap: wrap;
    }}
    .toc-item {{
      font-size: 13px;
      color: #444;
    }}
    .toc-item strong {{ color: #1e3a5f; font-size: 15px; }}
    .section {{ margin-bottom: 32px; }}
    .section-header {{
      display: flex;
      align-items: baseline;
      gap: 10px;
      border-left: 4px solid;
      padding-left: 12px;
      margin-bottom: 16px;
    }}
    .section-roman {{
      font-size: 15px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .section-label {{ font-size: 14px; }}
    .section-count {{
      margin-left: auto;
      font-size: 12px;
      background: #f0f0f0;
      color: #555;
      padding: 2px 8px;
      border-radius: 20px;
    }}
    .questions {{ display: flex; flex-direction: column; gap: 20px; }}
    .question {{
      border: 1px solid #e8e8e8;
      border-radius: 8px;
      padding: 14px 18px;
      background: #fafafa;
      page-break-inside: avoid;
    }}
    .question:hover {{ background: #f5f8ff; border-color: #c5d5f0; }}
    .q-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }}
    .q-num {{
      background: #1e3a5f;
      color: white;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      font-family: sans-serif;
    }}
    .badge {{
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      font-family: sans-serif;
    }}
    .badge.correct {{ background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7; }}
    .q-content {{ margin-bottom: 10px; }}
    .options {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin-top: 8px;
    }}
    .option {{
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 6px 10px;
      border: 1px solid #e5e5e5;
      border-radius: 6px;
      background: white;
      font-size: 14px;
    }}
    .opt-key {{
      font-weight: 700;
      color: #1e3a5f;
      min-width: 16px;
      font-family: sans-serif;
      font-size: 13px;
    }}
    .explanation {{
      margin-top: 10px;
      border-top: 1px dashed #e0e0e0;
      padding-top: 8px;
    }}
    .explanation summary {{
      cursor: pointer;
      font-size: 13px;
      color: #666;
      font-family: sans-serif;
      list-style: none;
    }}
    .explanation summary::-webkit-details-marker {{ display: none; }}
    .explanation-body {{
      margin-top: 8px;
      padding: 10px;
      background: #fffbeb;
      border-radius: 6px;
      font-size: 14px;
      color: #78350f;
    }}
    .katex {{ font-size: 1em; }}
    .katex-display {{ overflow-x: auto; margin: 6px 0; }}
    img {{ max-width: 100%; border-radius: 4px; }}
    table {{ border-collapse: collapse; margin: 8px 0; max-width: 100%; font-size: 14px; }}
    table td, table th {{ border: 1px solid #bbb; padding: 4px 10px; text-align: center; }}
    table tr:first-child td, table tr:first-child th {{ background: #f0f4fa; font-weight: 600; }}
    @media print {{
      body {{ background: white; }}
      .page {{ box-shadow: none; padding: 20px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header>
      <h1>{escape_html(title)}</h1>
      <div class="meta">Môn: Toán · Thời gian: 90 phút · {total} câu hỏi</div>
    </header>

    <div class="toc">
      <div class="toc-item">Phần I — Trắc nghiệm: <strong>{len(p1)}</strong> câu</div>
      <div class="toc-item">Phần II — Đúng/Sai: <strong>{len(p2)}</strong> câu</div>
      <div class="toc-item">Phần III — Tự luận: <strong>{len(p3)}</strong> câu</div>
    </div>

    {body}
  </div>
</body>
</html>"""


# ─── Main ───────────────────────────────────────────────────────────────────

async def main():
    # Fix Windows terminal encoding for Vietnamese output
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Đường dẫn file PDF")
    parser.add_argument("--skip-ocr",  action="store_true", help="Bỏ qua MinerU (dùng .md đã có)")
    parser.add_argument("--skip-norm", action="store_true", help="Bỏ qua normalize (dùng _normalized.md đã có)")
    parser.add_argument("--no-open",   action="store_true", help="Không tự mở browser")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        console.print(f"[red]✗ File không tồn tại: {pdf_path}[/red]")
        sys.exit(1)

    out_dir = config.PROCESSED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir = out_dir / "images"

    console.rule(f"[bold blue]preview_exam — {pdf_path.name}")

    # Step 1: OCR
    if not args.skip_ocr:
        md_path = run_ocr(pdf_path, out_dir)
    else:
        md_path = out_dir / f"{pdf_path.stem}.md"
        if not md_path.exists():
            console.print(f"[red]✗ Không tìm thấy {md_path} — bỏ --skip-ocr[/red]")
            sys.exit(1)
        console.print(f"[green]✓[/green] Skip OCR, dùng [cyan]{md_path.name}[/cyan]")

    raw_markdown = md_path.read_text(encoding="utf-8")
    console.print(f"  Markdown thô: {len(raw_markdown):,} chars")

    # Step 2: Normalize
    if not args.skip_norm:
        normalized = await normalize_markdown(raw_markdown, out_dir, pdf_path.stem)
    else:
        norm_path = out_dir / f"{pdf_path.stem}_normalized.md"
        if not norm_path.exists():
            console.print(f"[red]✗ Không tìm thấy {norm_path} — bỏ --skip-norm[/red]")
            sys.exit(1)
        normalized = norm_path.read_text(encoding="utf-8")
        console.print(f"[green]✓[/green] Skip normalize, dùng [cyan]{norm_path.name}[/cyan]")

    # Step 3: Parse
    console.print("[yellow]→[/yellow] Parse câu hỏi...")
    questions = parse_questions(normalized, img_dir)
    p1 = [q for q in questions if q["part"] == 1]
    p2 = [q for q in questions if q["part"] == 2]
    p3 = [q for q in questions if q["part"] == 3]
    console.print(
        f"[green]✓[/green] {len(questions)} câu: "
        f"P1={len(p1)} trắc nghiệm, P2={len(p2)} đúng/sai, P3={len(p3)} tự luận"
    )

    if not questions:
        console.print("[red]✗ Không parse được câu hỏi nào. Kiểm tra normalized markdown.[/red]")
        console.print(f"  Xem tại: {out_dir / f'{pdf_path.stem}_normalized.md'}")
        sys.exit(1)

    # Step 4: Render HTML
    title = pdf_path.stem.replace("_", " ").replace("-", " ")
    # Bỏ prefix năm nếu có
    title = re.sub(r'^\d{4}_\s*', '', title).strip()

    html = render_html(questions, title)
    html_path = out_dir / f"{pdf_path.stem}_preview.html"
    html_path.write_text(html, encoding="utf-8")

    console.print(f"\n[bold green]✅ Xong![/bold green]")
    console.print(f"   HTML: [cyan]{html_path}[/cyan]")
    console.print(f"   Normalized MD: [cyan]{out_dir / f'{pdf_path.stem}_normalized.md'}[/cyan]")

    if not args.no_open:
        webbrowser.open(html_path.resolve().as_uri())
        console.print("   [dim]Đã mở trong browser[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
