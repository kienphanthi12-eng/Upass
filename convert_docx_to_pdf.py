import os, sys, io, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path

def convert_docx_to_pdf(docx_path, pdf_path):
    abs_docx = str(Path(docx_path).resolve())
    abs_pdf = str(Path(pdf_path).resolve())
    print(f"Converting: {abs_docx} -> {abs_pdf}")
    
    # PowerShell command to convert docx to pdf using Word COM
    ps_cmd = (
        f"$word = New-Object -ComObject Word.Application; "
        f"$word.Visible = $false; "
        f"$doc = $word.Documents.Open('{abs_docx}'); "
        f"$doc.SaveAs('{abs_pdf}', 17); "
        f"$doc.Close(); "
        f"$word.Quit();"
    )
    
    try:
        res = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if res.returncode == 0:
            print("Conversion successful!")
            return True
        else:
            print(f"Conversion failed (return code {res.returncode}): {res.stderr or res.stdout}")
            return False
    except Exception as e:
        print(f"Error calling PowerShell: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_docx_to_pdf.py <docx_path> <pdf_path>")
        sys.exit(1)
        
    convert_docx_to_pdf(sys.argv[1], sys.argv[2])
