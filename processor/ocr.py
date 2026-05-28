"""
processor/ocr.py — OCR PDF bằng MinerU Cloud API (mineru.net)
Flow (v4 batch upload):
  1. POST /api/v4/file-urls/batch  → nhận batch_id + pre-signed OSS upload URLs
  2. PUT file binary lên OSS URL    → không cần auth header
  3. GET /api/v4/extract/task/batch/{batch_id} → poll cho đến done
  4. Download zip từ full_zip_url, extract .md
Không cần cài gì local, chỉ cần MINERU_API_KEY.
"""
import io
import logging
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Optional

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config

logger = logging.getLogger(__name__)

# ─── MinerU API constants ─────────────────────────────────────────────────────
MINERU_BASE           = "https://mineru.net/api/v4"
ENDPOINT_FILE_URLS    = f"{MINERU_BASE}/file-urls/batch"               # POST: lấy pre-signed URLs
ENDPOINT_BATCH_STATUS = f"{MINERU_BASE}/extract-results/batch/{{bid}}" # GET: poll batch results


# ─── MinerU API Client ────────────────────────────────────────────────────────

class MinerUClient:
    """
    Client cho MinerU Cloud API v4 (batch upload flow).
    Docs: https://mineru.net/apiManage/docs

    Lấy API key tại: https://mineru.net/apiManage/list
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.MINERU_API_KEY
        if not self.api_key:
            raise ValueError(
                "MINERU_API_KEY chưa set!\n"
                "1. Đăng ký tại https://mineru.net\n"
                "2. Lấy token tại https://mineru.net/apiManage/list\n"
                "3. Thêm vào .env: MINERU_API_KEY=your_token"
            )
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    # ── Step 1: Lấy pre-signed upload URL qua batch endpoint ─────────────────

    def request_upload_url(
        self,
        file_name: str,
        data_id: str = None,
        enable_formula: bool = True,
        enable_table: bool = True,
        language: str = "ch",
        is_ocr: bool = True,
    ) -> dict:
        """
        POST /api/v4/file-urls/batch với 1 file.
        Trả về: {"batch_id": "...", "upload_url": "..."}
        """
        payload = {
            "files": [{"name": file_name, "data_id": data_id or file_name}],
            "enable_formula": enable_formula,
            "enable_table":   enable_table,
            "language":       language,
            "is_ocr":         is_ocr,
        }
        resp = self.session.post(ENDPOINT_FILE_URLS, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"MinerU file-urls error: {data.get('msg', data)}")

        batch_id   = data["data"]["batch_id"]
        upload_url = data["data"]["file_urls"][0]
        return {"batch_id": batch_id, "upload_url": upload_url}

    # ── Step 2: Upload file binary lên pre-signed OSS URL ────────────────────

    def upload_file(self, upload_url: str, pdf_path: str) -> None:
        """PUT file binary lên OSS pre-signed URL — không cần auth, không set Content-Type."""
        with open(pdf_path, "rb") as f:
            content = f.read()

        resp = requests.put(upload_url, data=content, timeout=300)
        if resp.status_code not in (200, 204):
            raise RuntimeError(
                f"OSS upload failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )
        logger.debug(f"Upload OK: {len(content) // 1024} KB")

    # ── Step 3: Poll batch cho đến khi done ───────────────────────────────────

    def poll_batch(
        self,
        batch_id: str,
        timeout: int = 600,   # 10 phút
        interval: int = 5,    # check mỗi 5 giây
    ) -> dict:
        """
        Poll batch status cho đến khi file đầu tiên xong.
        Trả về result dict của file đó khi hoàn tất.
        """
        url = ENDPOINT_BATCH_STATUS.format(bid=batch_id)
        state_labels = {
            "waiting": "Chờ xử lý",
            "pending": "Đang xếp hàng",
            "running": "Đang parse PDF",
            "done":    "Hoàn tất",
            "failed":  "Thất bại",
        }
        deadline   = time.time() + timeout
        last_state = ""

        while time.time() < deadline:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(f"Batch poll error: {data.get('msg')}")

            batch_data = data["data"]

            # Batch result có thể là list hoặc dict với key "extract_result"
            files_list = (
                batch_data.get("extract_result")
                or batch_data.get("list")
                or (batch_data if isinstance(batch_data, list) else [batch_data])
            )

            if files_list:
                file_result = files_list[0]
                state = file_result.get("state", "")

                if state != last_state:
                    label = state_labels.get(state, state)
                    logger.info(f"  MinerU batch [{batch_id[:8]}...]: {label}")
                    last_state = state

                if state == "done":
                    return file_result
                elif state == "failed":
                    raise RuntimeError(
                        f"MinerU task failed: {file_result.get('err_msg', 'unknown error')}"
                    )

            time.sleep(interval)

        raise TimeoutError(f"MinerU batch {batch_id} timeout sau {timeout}s")

    # ── Step 4: Download markdown từ kết quả ─────────────────────────────────

    def download_markdown(self, result: dict, image_dir: str = None) -> str:
        """Download zip từ full_zip_url, extract .md và ảnh vào image_dir."""
        zip_url = (
            result.get("full_zip_url")
            or result.get("zip_url")
            or result.get("result_url")
            or self._find_url(result)
        )

        if not zip_url:
            pages = result.get("pages") or []
            if pages:
                return "\n\n".join(p.get("markdown", "") for p in pages if p.get("markdown"))
            raise ValueError(f"Không tìm thấy zip URL trong result. Keys: {list(result.keys())}")

        if ".zip" in zip_url:
            return self._download_zip_markdown(zip_url, image_dir=image_dir)

        resp = requests.get(zip_url, timeout=60)
        resp.raise_for_status()
        return resp.text

    def _find_url(self, result: dict) -> str:
        """Tìm URL trong các field lồng nhau."""
        for key in ["md_url", "markdown_url", "content_url", "output_url"]:
            if key in result and result[key]:
                return result[key]
        for val in result.values():
            if isinstance(val, dict):
                found = self._find_url(val)
                if found:
                    return found
        return ""

    def _download_zip_markdown(self, zip_url: str, image_dir: str = None) -> str:
        """Download zip, extract markdown + images. Save images to image_dir if given."""
        resp = requests.get(zip_url, timeout=120)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            md_files = [n for n in zf.namelist() if n.endswith(".md")]
            if not md_files:
                raise ValueError("Không có file .md trong zip")
            md_file = max(md_files, key=lambda n: zf.getinfo(n).file_size)
            markdown = zf.read(md_file).decode("utf-8")

            if image_dir:
                img_dir = Path(image_dir)
                img_dir.mkdir(parents=True, exist_ok=True)
                img_exts = re.compile(r'\.(jpg|jpeg|png|gif|webp)$', re.I)
                for name in zf.namelist():
                    if img_exts.search(name):
                        filename = Path(name).name
                        dest = img_dir / filename
                        if not dest.exists():
                            dest.write_bytes(zf.read(name))
                        logger.debug(f"  Image: {filename}")

        return markdown

    # ── Hàm tổng hợp: xử lý 1 PDF ────────────────────────────────────────────

    def parse_pdf(
        self,
        pdf_path: str,
        save_markdown_to: str = None,
        image_dir: str = None,
        **kwargs,
    ) -> dict:
        """
        Full flow (v4 batch upload): request URL → upload → poll → download markdown.
        Trả về dict kết quả đầy đủ.
        """
        pdf_path = Path(pdf_path)
        file_name = pdf_path.name
        file_size_mb = pdf_path.stat().st_size / 1024 / 1024

        logger.info(f"MinerU API: parsing {file_name} ({file_size_mb:.1f} MB)")

        enable_formula = kwargs.pop("enable_formula", True)
        enable_table   = kwargs.pop("enable_table", True)
        language       = kwargs.pop("language", "ch")
        is_ocr         = kwargs.pop("is_ocr", True)

        # Step 1: Lấy pre-signed URL
        upload_info = self.request_upload_url(
            file_name,
            enable_formula=enable_formula,
            enable_table=enable_table,
            language=language,
            is_ocr=is_ocr,
        )
        batch_id   = upload_info["batch_id"]
        upload_url = upload_info["upload_url"]
        logger.info(f"  Batch ID: {batch_id}")

        # Step 2: Upload
        logger.info("  Uploading PDF to OSS...")
        self.upload_file(upload_url, str(pdf_path))

        # Step 3: Poll
        logger.info("  Waiting for MinerU to process...")
        result = self.poll_batch(batch_id)

        # Step 4: Download markdown + images
        markdown = self.download_markdown(result, image_dir=image_dir)
        logger.info(f"  Markdown: {len(markdown)} chars")

        if save_markdown_to:
            Path(save_markdown_to).write_text(markdown, encoding="utf-8")

        return {
            "task_id":     batch_id,
            "markdown":    markdown,
            "result":      result,
            "has_formula": _has_formula(markdown),
            "has_image":   _has_image(markdown),
            "has_table":   _has_table(markdown),
            "page_count":  result.get("total_pages") or result.get("page_count") or 0,
        }


# ─── Detect content types ─────────────────────────────────────────────────────

def _has_formula(md: str) -> bool:
    return bool(re.search(r'\$[^$\n]+\$|\$\$[\s\S]+?\$\$', md))

def _has_image(md: str) -> bool:
    return bool(re.search(r'!\[.*?\]\(.*?\)', md))

def _has_table(md: str) -> bool:
    return "| " in md and "\n|" in md


# ─── Question parser ──────────────────────────────────────────────────────────

class QuestionParser:
    """
    Tách câu hỏi từ markdown MinerU output.
    Xử lý nhiều format đề thi THPT.
    """

    def parse(self, markdown: str) -> list:
        text = self._normalize(markdown)

        # Split by question patterns: "Cau 1.", "Câu 1:", "Question 5." etc.
        # These can appear at the start of a paragraph or mid-paragraph
        pattern = r'(?:^|\n\s*)[Cc]a[â]?u\s+(\d+)\s*[:\.\s]'
        matches = list(re.finditer(pattern, text, re.MULTILINE))

        if not matches:
            # Fallback: try "Question N."
            pattern = r'(?:^|\n\s*)Question\s+(\d+)[:\.\s]'
            matches = list(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE))

        questions = []
        for i, m in enumerate(matches):
            q_num = int(m.group(1))
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            raw = text[start:end].strip()
            if len(raw) < 15:
                continue
            # Prepend "Cau N. " to content for context
            full_text = m.group(0).strip() + " " + raw
            content, options = self._extract_options(full_text)
            questions.append({
                "number":      q_num,
                "content":     content,
                "content_raw": full_text,
                "options":     options,
                "has_formula": _has_formula(full_text),
                "has_image":   _has_image(full_text),
                "has_table":   _has_table(full_text),
            })

        logger.info(f"Parsed {len(questions)} questions")
        return questions

    def _extract_options(self, text: str) -> tuple:
        """Tách thân câu và 4 đáp án A B C D.

        Hỗ trợ các format đề THPT:
          1. Mỗi đáp án trên dòng riêng
          2. Inline với separator . hoặc )
          3. A không có separator, B/C/D có separator
          4. Không có separator (A trực tiếp đến text)
          5. Terminal-period: "A content. B content. C content. D content."
        """
        # Pre-normalize OCR artifacts common in THPT scans
        text = text.replace('④', 'A')   # ④ (circled 4) → A
        text = text.replace('@', 'C')              # @ → C (OCR misread)
        text = re.sub(r'(?<=\s)\.([ABCD])\.', r'\1.', text, flags=re.IGNORECASE)  # .B. → B.

        # --- Strategy 1: Options trên dòng riêng ---
        newline_pat = re.compile(
            r'(?:^|\n)\s*([ABCD])[.)]\s*(.+?)(?=\n\s*[ABCD][.)]|\Z)',
            re.DOTALL | re.MULTILINE | re.IGNORECASE
        )
        nl_matches = list(newline_pat.finditer(text))
        nl_keys = {m.group(1).upper() for m in nl_matches}
        if len(nl_keys) >= 3:
            content = text[:nl_matches[0].start()].strip()
            options = {}
            for m in nl_matches:
                options[m.group(1).upper()] = re.sub(r'\s+', ' ', m.group(2)).strip()
            if len(options) >= 3:
                return content, options

        flat = ' ' + re.sub(r'\s+', ' ', text).strip() + ' '

        # --- Strategy 2: Inline với separator . hoặc ) ---
        for a_pos in reversed([m.start() for m in re.finditer(r' A[.)]', flat, re.IGNORECASE)]):
            after_a = flat[a_pos + 3:]
            b_m = re.search(r' B[.)]', after_a, re.IGNORECASE)
            if not b_m:
                continue
            a_text = after_a[:b_m.start()].strip()
            after_b = after_a[b_m.end():]
            c_m = re.search(r' C[.)]', after_b, re.IGNORECASE)
            if not c_m:
                continue
            b_text = after_b[:c_m.start()].strip()
            after_c = after_b[c_m.end():]
            d_m = re.search(r' D[.)]', after_c, re.IGNORECASE)
            if not d_m:
                continue
            c_text = after_c[:d_m.start()].strip()
            d_text = after_c[d_m.end():].strip()
            if not all([a_text, b_text, c_text, d_text]):
                continue
            if any(len(t) > 400 for t in [a_text, b_text, c_text, d_text]):
                continue
            options = {'A': a_text, 'B': b_text, 'C': c_text, 'D': d_text}
            content = flat[:a_pos].strip()
            return content, options

        # --- Strategy 3: A không có separator, B/C/D có separator ---
        for a_pos in reversed([m.start() for m in re.finditer(r' A(?=[^.)\s]|\s*\$)', flat, re.IGNORECASE)]):
            after_a = flat[a_pos + 2:]
            b_m = re.search(r' B[.)]', after_a, re.IGNORECASE)
            if not b_m or b_m.start() > 400:
                continue
            a_text = after_a[:b_m.start()].strip()
            after_b = after_a[b_m.end():]
            c_m = re.search(r' C[.)]', after_b, re.IGNORECASE)
            if not c_m or c_m.start() > 400:
                continue
            b_text = after_b[:c_m.start()].strip()
            after_c = after_b[c_m.end():]
            d_m = re.search(r' D[.)]', after_c, re.IGNORECASE)
            if not d_m:
                continue
            c_text = after_c[:d_m.start()].strip()
            d_text = after_c[d_m.end():].strip()
            if not all([a_text, b_text, c_text, d_text]):
                continue
            if any(len(t) > 400 for t in [a_text, b_text, c_text, d_text]):
                continue
            options = {'A': a_text, 'B': b_text, 'C': c_text, 'D': d_text}
            content = flat[:a_pos].strip()
            return content, options

        # --- Strategy 4: No separator (e.g. "A $formula$ B $formula$ C ... D ...") ---
        # Search full flat; reversed() ensures we grab the last valid A/B/C/D sequence
        for a_pos in reversed([m.start() for m in re.finditer(r' A(?=[^.)\s]|\s*\$)', flat, re.IGNORECASE)]):
            after_a = flat[a_pos + 2:]
            b_m = re.search(r' B(?=[^.)\s]|\s*\$)', after_a, re.IGNORECASE)
            if not b_m or b_m.start() > 300:
                continue
            a_text = after_a[:b_m.start()].strip()
            after_b = after_a[b_m.end():]
            c_m = re.search(r' C(?=[^.)\s]|\s*\$)', after_b, re.IGNORECASE)
            if not c_m or c_m.start() > 300:
                continue
            b_text = after_b[:c_m.start()].strip()
            after_c = after_b[c_m.end():]
            d_m = re.search(r' D(?=[^.)\s]|\s*\$)', after_c, re.IGNORECASE)
            if not d_m:
                continue
            c_text = after_c[:d_m.start()].strip()
            d_text = after_c[d_m.end():].strip()
            if not all([a_text, b_text, c_text, d_text]):
                continue
            if any(len(t) > 300 for t in [a_text, b_text, c_text, d_text]):
                continue
            options = {'A': a_text, 'B': b_text, 'C': c_text, 'D': d_text}
            content = flat[:a_pos].strip()
            return content, options

        # --- Strategy 5: Terminal-period format ---
        # Handles "A [2;11]. B (2;8]. C(-∞;11]. D (2;11]." (short non-LaTeX options)
        m5 = re.search(
            r' A\s*((?:(?!\. *[ABCD]\b).)+)\. *B\s*((?:(?!\. *[ABCD]\b).)+)\. *C\s*((?:(?!\. *D\b).)+)\. *D\s*(.+?)\.?\s*$',
            flat, re.IGNORECASE | re.DOTALL
        )
        if m5:
            a_text, b_text, c_text, d_text = [x.strip() for x in m5.groups()]
            if all([a_text, b_text, c_text, d_text]):
                if not any(len(t) > 150 for t in [a_text, b_text, c_text, d_text]):
                    options = {'A': a_text, 'B': b_text, 'C': c_text, 'D': d_text}
                    a_start = flat.index(' A')
                    content = flat[:a_start].strip()
                    return content, options

        return text.strip(), None

    @staticmethod
    def _normalize(text: str) -> str:
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n\s*[-–]\s*\d+\s*[-–]\s*\n', '\n', text)  # số trang
        text = re.sub(r'\nTrang \d+/\d+\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


# ─── Public interface (dùng trong pipeline) ───────────────────────────────────

class MinerUProcessor:
    """Drop-in replacement cho local MinerU, dùng Cloud API."""

    def __init__(self, output_dir: Path = None, api_key: str = None):
        self.output_dir = output_dir or config.PROCESSED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = MinerUClient(api_key)

    def process(self, pdf_path: str, image_dir: str = None) -> Optional[dict]:
        """
        OCR một file PDF qua MinerU API.
        Trả về dict tương thích với phiên bản local cũ.
        """
        pdf_path = Path(pdf_path)
        md_save  = self.output_dir / f"{pdf_path.stem}.md"

        try:
            result = self.client.parse_pdf(
                str(pdf_path),
                save_markdown_to=str(md_save),
                image_dir=image_dir,
                enable_formula=True,
                enable_table=True,
                is_ocr=True,
                language="vi",
            )
            return {
                "markdown":    result["markdown"],
                "content_list": [],
                "has_formula": result["has_formula"],
                "has_image":   result["has_image"],
                "has_table":   result["has_table"],
                "page_count":  result["page_count"],
                "output_dir":  str(self.output_dir),
                "task_id":     result["task_id"],
            }
        except Exception as e:
            logger.error(f"MinerU API failed for {pdf_path.name}: {e}")
            return None


def process_pdf(pdf_path: str, output_dir: Path = None) -> Optional[dict]:
    """Hàm tiện lợi: OCR + parse câu hỏi từ 1 PDF."""
    processor = MinerUProcessor(output_dir)
    ocr_result = processor.process(pdf_path)
    if not ocr_result:
        return None
    parser = QuestionParser()
    questions = parser.parse(ocr_result["markdown"])
    return {"ocr": ocr_result, "questions": questions}
