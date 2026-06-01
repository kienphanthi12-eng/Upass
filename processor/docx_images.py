"""
processor/docx_images.py — Trích ảnh inline (kể cả công thức MathType/WMF) từ DOCX.

Vấn đề: đề KHTN thường nhúng công thức dưới dạng OLE object (MathType) với ảnh xem trước
WMF, hoặc DrawingML (PNG). python-docx chỉ trả `paragraph.text` (plain) → mất công thức.

Module này duyệt XML của paragraph theo đúng thứ tự document, tách thành các đoạn xen kẽ
text / ảnh, và convert WMF/EMF → PNG (PIL) để hiển thị được trên web. Nhờ vậy parser tái
dựng được content kèm `![](...)` đúng vị trí (vd `A. ![](f1.png)  B. ![](f2.png)`).

Hai cơ chế nhúng ảnh được hỗ trợ:
  - DrawingML hiện đại:  <w:drawing> … <a:blip r:embed="rId">
  - OLE/VML (MathType):  <w:object>/<w:pict> … <v:imagedata r:id="rId">
"""
from __future__ import annotations

import io
from typing import Callable, Optional

from docx.oxml.ns import qn

# Namespace VML (python-docx không có sẵn trong qn) và relationships
_NS_V = "urn:schemas-microsoft-com:vml"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Ảnh giữ nguyên (web hiển thị được); các loại khác sẽ convert sang PNG
_PASSTHROUGH_EXT = {"png", "jpg", "jpeg", "gif", "bmp"}
_VECTOR_EXT = {"wmf", "emf", "x-wmf", "x-emf"}


def _rid_from_drawing(drawing_el) -> Optional[str]:
    """Lấy rId từ <w:drawing> (DrawingML → a:blip r:embed)."""
    blip = drawing_el.find(".//" + qn("a:blip"))
    if blip is not None:
        rid = blip.get(qn("r:embed")) or blip.get(qn("r:link"))
        if rid:
            return rid
    return None


def _rid_from_vml(el) -> Optional[str]:
    """Lấy rId từ <w:object>/<w:pict> (VML → v:imagedata r:id)."""
    imagedata = el.find(".//{%s}imagedata" % _NS_V)
    if imagedata is not None:
        rid = imagedata.get("{%s}id" % _NS_R)
        if rid:
            return rid
    # Một số file dùng a:blip lồng trong object
    blip = el.find(".//" + qn("a:blip"))
    if blip is not None:
        return blip.get(qn("r:embed"))
    return None


def _iter_run_children(run_el):
    """Yield ('text', str) hoặc ('image', rId) từ 1 phần tử <w:r> theo thứ tự."""
    for child in run_el:
        tag = child.tag
        if tag == qn("w:t"):
            yield ("text", child.text or "")
        elif tag == qn("w:tab"):
            yield ("text", "\t")
        elif tag in (qn("w:br"), qn("w:cr")):
            yield ("text", "\n")
        elif tag == qn("w:drawing"):
            rid = _rid_from_drawing(child)
            if rid:
                yield ("image", rid)
        elif tag in (qn("w:object"), qn("w:pict")):
            rid = _rid_from_vml(child)
            if rid:
                yield ("image", rid)


def paragraph_segments(paragraph) -> list[tuple[str, str]]:
    """
    Duyệt paragraph theo thứ tự document → list các đoạn:
        ("text", "<nội dung>")  |  ("image", "<rId>")

    Hỗ trợ run trực tiếp và run nằm trong <w:hyperlink>.
    """
    segments: list[tuple[str, str]] = []
    for child in paragraph._p:
        tag = child.tag
        if tag == qn("w:r"):
            segments.extend(_iter_run_children(child))
        elif tag == qn("w:hyperlink"):
            for run_el in child.findall(qn("w:r")):
                segments.extend(_iter_run_children(run_el))
    return segments


def has_inline_image(paragraph) -> bool:
    """True nếu paragraph có ít nhất 1 ảnh inline (drawing/object/pict)."""
    p = paragraph._p
    return bool(
        p.findall(".//" + qn("w:drawing"))
        or p.findall(".//" + qn("w:object"))
        or p.findall(".//" + qn("w:pict"))
    )


def image_to_png_bytes(part, rid: str) -> Optional[tuple[bytes, str]]:
    """
    Resolve rId → bytes ảnh. Convert WMF/EMF → PNG (PIL). PNG/JPEG giữ nguyên.

    Trả (data, ext) hoặc None nếu không resolve được.
    """
    try:
        image_part = part.related_parts[rid]
    except (KeyError, AttributeError):
        return None

    data = image_part.blob
    # Suy ext từ partname (vd word/media/image5.wmf) hoặc content_type
    partname = str(getattr(image_part, "partname", "")).lower()
    ext = partname.rsplit(".", 1)[-1] if "." in partname else ""
    if not ext:
        ct = getattr(image_part, "content_type", "") or ""
        ext = ct.rsplit("/", 1)[-1].lower()

    if ext in _PASSTHROUGH_EXT:
        return data, ("jpg" if ext == "jpeg" else ext)

    if ext in _VECTOR_EXT or "wmf" in ext or "emf" in ext:
        png = _vector_to_png(data)
        if png is not None:
            return png, "png"
        return None  # không render được → bỏ (tránh chèn ảnh web không hiển thị)

    # Định dạng lạ: thử mở bằng PIL, nếu được thì xuất PNG
    png = _vector_to_png(data)
    if png is not None:
        return png, "png"
    return None


def _vector_to_png(data: bytes) -> Optional[bytes]:
    """Convert WMF/EMF (hoặc bất kỳ thứ gì PIL mở được) → PNG bytes."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im.load()
        # Upscale ảnh công thức quá nhỏ cho dễ đọc (vector rasterize ở size logic)
        if im.width and im.width < 240:
            scale = min(4, max(2, 240 // max(im.width, 1)))
            im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        out = io.BytesIO()
        im.save(out, "PNG")
        return out.getvalue()
    except Exception:
        return None


def render_paragraph(
    paragraph,
    image_saver: Callable[[bytes, str], Optional[str]],
) -> str:
    """
    Dựng lại nội dung paragraph thành text, chèn ảnh inline đúng vị trí.

    `image_saver(png_bytes, ext) -> markdown_ref|None`: do parser cung cấp; lưu ảnh xuống đĩa/
    upload rồi trả về chuỗi markdown (vd "![](abs/path.png)"). Trả None nếu muốn bỏ ảnh.

    Trả về text đã ghép (text thường + ![](...) ).
    """
    part = paragraph.part
    parts: list[str] = []
    for kind, value in paragraph_segments(paragraph):
        if kind == "text":
            parts.append(value)
        else:  # image
            got = image_to_png_bytes(part, value)
            if not got:
                continue
            data, ext = got
            ref = image_saver(data, ext)
            if ref:
                parts.append(ref)
    return "".join(parts)
