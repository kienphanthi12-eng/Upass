"""
test_smart_parser.py — Kiểm thử smart_parser trên đề thực tế.
Chạy: python test_smart_parser.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from processor.smart_parser import parse_exam_file, split_document, parse_answer_table, parse_solutions
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

TEST_FILES = [
    Path("C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-TN-THPT-2026-mon-VAT-LI-GD-DONG-NAI.pdf-62b68da5-d3d1-409d-9000-5a57804a6474/full.md"),
    Path("C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-Tot-Nghiep-2026-Hoa-So-GD-Lam-Dong-.pdf-2ddd6d08-eeef-4b2e-bd31-238b5b76f028/full.md"),
    Path("C:/Users/HP/MinerU/thuvienhoclieu.com-De-thi-thu-Tn-THPT-nam-2026-Vat-Li-So-GD-Ca-Mau-Lan-1.pdf-f12f691a-7409-42a1-b2fd-7f8ed19bdc63/full.md"),
]

def print_question_sample(q, max_text=80):
    txt = q.question_text[:max_text].replace("\n", " ")
    if len(q.question_text) > max_text:
        txt += "…"
    ans = q.correct_answer or "—"
    exp = "✅" if q.explanation else "—"
    opts = f"{len(q.options)} opts" if q.options else "none"
    return f"[{q.q_type[:4]}] Q{q.index} | ans={ans} | exp={exp} | {opts} | {txt}"

for fpath in TEST_FILES:
    if not fpath.exists():
        console.print(f"[yellow]File không tồn tại: {fpath.name}[/]")
        continue

    console.print(Panel(f"[bold cyan]{fpath.parent.name[:70]}[/]", expand=False))

    raw = fpath.read_text(encoding="utf-8")

    # ─── Test split_document ────────────────────────────────────────────────
    exam_body, answer_block, solution_raw = split_document(raw)
    console.print(f"  📄 exam_body   : [green]{len(exam_body):,}[/] chars")
    console.print(f"  📋 answer_block: [green]{len(answer_block):,}[/] chars")
    console.print(f"  📝 solution    : [green]{len(solution_raw):,}[/] chars")

    # ─── Test answer table ──────────────────────────────────────────────────
    answers = parse_answer_table(answer_block + "\n" + solution_raw[:4000])
    console.print(f"  🗝  Đáp án parsed: [bold]{len(answers)}[/] câu")
    # Group by section
    by_sec = {}
    for (sec, qn), ans in sorted(answers.items()):
        by_sec.setdefault(sec, {})[qn] = ans
    for sec, qmap in sorted(by_sec.items()):
        nums = sorted(qmap.keys())
        preview = "  ".join(f"{n}:{qmap[n]}" for n in nums[:8])
        console.print(f"     Phần {sec} ({len(qmap)} câu): {preview}{'…' if len(nums)>8 else ''}")

    # ─── Test full parse ────────────────────────────────────────────────────
    exams = parse_exam_file(raw)
    console.print(f"\n  📦 Số đề detect: [bold]{len(exams)}[/]")

    for exam in exams:
        console.print(f"  Môn: [cyan]{exam.subject}[/]  Mã đề: [cyan]{exam.ma_de}[/]  Câu: [cyan]{len(exam.questions)}[/]")

        t = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        t.add_column("Sec", width=3)
        t.add_column("Idx", width=3)
        t.add_column("Type", width=12)
        t.add_column("Answer", width=8)
        t.add_column("Exp", width=4)
        t.add_column("Options", width=6)
        t.add_column("Question (preview)", no_wrap=True, max_width=60)

        # Group stats
        by_type = {}
        missing_ans = 0
        missing_exp = 0

        for q in exam.questions:
            by_type[q.q_type] = by_type.get(q.q_type, 0) + 1
            if not q.correct_answer:
                missing_ans += 1
            if not q.explanation:
                missing_exp += 1

            txt = q.question_text[:60].replace("\n", " ")
            opts = f"{len(q.options)}" if q.options else "0"
            t.add_row(
                str(q.section),
                str(q.index),
                q.q_type,
                q.correct_answer or "[red]—[/]",
                "✅" if q.explanation else "[dim]—[/]",
                opts,
                txt,
            )

        console.print(t)

        console.print(f"  📊 Phân loại: {by_type}")
        console.print(f"  ⚠️  Thiếu đáp án: [{'red' if missing_ans else 'green'}]{missing_ans}[/] / {len(exam.questions)}")
        console.print(f"  ⚠️  Thiếu lời giải: [{'yellow' if missing_exp else 'green'}]{missing_exp}[/] / {len(exam.questions)}")

    console.print()

console.print("[bold green]✅ Test xong![/]")
