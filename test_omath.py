import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from docx import Document
from lxml import etree

doc = Document("data/pdfs/test_vatly_lamdong.docx")
p2 = doc.paragraphs[4] # Câu 2
xml_str = etree.tostring(p2._element, pretty_print=True).decode('utf-8')

# Search for any attributes or text nodes inside <w:object>
root = etree.fromstring(xml_str.encode('utf-8'))
for elem in root.iter():
    # If it has attributes, print them
    attribs = {k.split("}")[-1]: v for k, v in elem.attrib.items()}
    if attribs:
        # Check if any attribute has math-like symbols or text
        for k, v in attribs.items():
            if any(sym in str(v) for sym in ["=", "+", "-", "/", "^", "_", "\\", "v", "p", "m"]):
                print(f"Tag: {elem.tag.split('}')[-1]} | Attr: {k} = {v}")
