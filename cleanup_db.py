"""
cleanup_db.py — Dọn dẹp DB sau khi pipeline chạy xong:
  1. Xóa các exam trùng lặp (cùng title, giữ lại exam_id nhỏ nhất)
  2. Xóa câu hỏi tu_luan dư thừa: giữ tối đa 7 câu mỗi phần III
     (question_number 201-207, xóa 208+)

Cách dùng:
  python cleanup_db.py --dry   # xem trước, không xóa
  python cleanup_db.py         # thực sự xóa
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from database import db

DRY = "--dry" in sys.argv

# ─── Giới hạn: chỉ dọn các exam mới (id > 104) ───────────────────────────────
# Các exam cũ (75-104) đã ổn, không cần đụng tới.
NEW_EXAM_MIN_ID = 104


def report(msg: str):
    print(msg)


def step1_delete_duplicate_exams(conn) -> int:
    """Xóa exam trùng title trong nhóm id > NEW_EXAM_MIN_ID. Giữ lại id nhỏ nhất."""
    with conn.cursor() as cur:
        # Tìm duplicate
        cur.execute("""
            SELECT title,
                   COUNT(*) AS cnt,
                   MIN(id)  AS keep_id,
                   ARRAY_AGG(id ORDER BY id) AS all_ids
            FROM exams
            WHERE id > %s
            GROUP BY title
            HAVING COUNT(*) > 1
            ORDER BY title
        """, (NEW_EXAM_MIN_ID,))
        dupes = cur.fetchall()

    if not dupes:
        report("  [OK] Không có exam trùng lặp.")
        return 0

    to_delete = []
    for title, cnt, keep_id, all_ids in dupes:
        del_ids = [i for i in all_ids if i != keep_id]
        report(f"  • \"{title[:60]}\" — {cnt} bản, giữ id={keep_id}, xóa {del_ids}")
        to_delete.extend(del_ids)

    report(f"\n  → Tổng {len(to_delete)} exam duplicate sẽ bị xóa (CASCADE questions)")
    if DRY:
        report("  [DRY] Không xóa thật.")
        return 0

    with conn.cursor() as cur:
        cur.execute("DELETE FROM exams WHERE id = ANY(%s)", (to_delete,))
        deleted = cur.rowcount
    conn.commit()
    report(f"  [OK] Đã xóa {deleted} exam (questions bị xóa theo CASCADE).")
    return deleted


def step2_fix_tu_luan(conn) -> int:
    """
    Dọn tu_luan cho các exam mới:
      2A) Xóa bản trùng (exam_id, question_number) — giữ id nhỏ nhất mỗi số câu
      2B) Xóa câu có question_number > 207 (lời giải fragment — giữ tối đa 7 câu P3)
    """
    # ── 2A: dedup by (exam_id, question_number) ──────────────────────────────
    with conn.cursor() as cur:
        cur.execute("""
            SELECT exam_id, question_number, COUNT(*) AS cnt, MIN(id) AS keep_id
            FROM questions
            WHERE question_type = 'tu_luan'
              AND exam_id IN (SELECT id FROM exams WHERE id > %s)
            GROUP BY exam_id, question_number
            HAVING COUNT(*) > 1
            ORDER BY exam_id, question_number
        """, (NEW_EXAM_MIN_ID,))
        dup_rows = cur.fetchall()

    total_dup = sum(r[2] - 1 for r in dup_rows)
    if dup_rows:
        report(f"  2A) {len(dup_rows)} (exam,q_num) bị trùng — sẽ xóa {total_dup} bản thừa")
        if not DRY:
            with conn.cursor() as cur:
                # Xóa tất cả trừ id nhỏ nhất
                cur.execute("""
                    DELETE FROM questions
                    WHERE question_type = 'tu_luan'
                      AND exam_id IN (SELECT id FROM exams WHERE id > %s)
                      AND id NOT IN (
                          SELECT MIN(id)
                          FROM questions
                          WHERE question_type = 'tu_luan'
                            AND exam_id IN (SELECT id FROM exams WHERE id > %s)
                          GROUP BY exam_id, question_number
                      )
                """, (NEW_EXAM_MIN_ID, NEW_EXAM_MIN_ID))
                deleted_dup = cur.rowcount
            conn.commit()
            report(f"  [OK] Đã xóa {deleted_dup} bản trùng tu_luan.")
    else:
        report("  2A) Không có tu_luan bị trùng (exam, q_num).")

    # ── 2B: trim question_number > 207 ───────────────────────────────────────
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.id, e.title,
                   COUNT(*) FILTER (WHERE q.question_type = 'tu_luan') AS total_tl,
                   COUNT(*) FILTER (WHERE q.question_type = 'tu_luan' AND q.question_number > 207) AS excess
            FROM exams e
            JOIN questions q ON q.exam_id = e.id
            WHERE e.id > %s
            GROUP BY e.id, e.title
            HAVING COUNT(*) FILTER (WHERE q.question_type = 'tu_luan' AND q.question_number > 207) > 0
            ORDER BY excess DESC
        """, (NEW_EXAM_MIN_ID,))
        rows = cur.fetchall()

    if not rows:
        report("  2B) Không có tu_luan nào vượt question_number 207.")
        return 0

    total_excess = 0
    for exam_id, title, total_tl, excess in rows:
        report(f"  • exam_id={exam_id} \"{title[:55]}\" — tu_luan={total_tl}, xóa q>207: {excess}")
        total_excess += excess

    report(f"\n  → 2B) Tổng {total_excess} câu tu_luan (q>207) sẽ bị xóa")
    if DRY:
        report("  [DRY] Không xóa thật.")
        return 0

    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM questions
            WHERE question_type = 'tu_luan'
              AND question_number > 207
              AND exam_id IN (SELECT id FROM exams WHERE id > %s)
        """, (NEW_EXAM_MIN_ID,))
        deleted = cur.rowcount
    conn.commit()
    report(f"  [OK] Đã xóa {deleted} câu tu_luan q>207.")
    return deleted


def step3_show_summary(conn):
    """In bảng tổng quan các exam mới sau khi cleanup."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.id, e.title,
                   COUNT(q.id) AS total_q,
                   COUNT(*) FILTER (WHERE q.question_type = 'trac_nghiem') AS p1,
                   COUNT(*) FILTER (WHERE q.question_type = 'dung_sai')    AS p2,
                   COUNT(*) FILTER (WHERE q.question_type = 'tu_luan')     AS p3,
                   COUNT(*) FILTER (WHERE q.explanation IS NOT NULL AND q.explanation != '') AS with_expl
            FROM exams e
            LEFT JOIN questions q ON q.exam_id = e.id
            WHERE e.id > %s
            GROUP BY e.id, e.title
            ORDER BY e.id
        """, (NEW_EXAM_MIN_ID,))
        rows = cur.fetchall()

    print()
    print(f"{'ID':>5}  {'Tên đề':<50}  {'Tổng':>5}  P1  P2  P3  Expl")
    print("-" * 90)
    for exam_id, title, total, p1, p2, p3, expl in rows:
        ok_flag = "✓" if 18 <= total <= 24 else ("?" if 15 <= total <= 30 else "⚠")
        print(f"{exam_id:>5}  {title[:50]:<50}  {total:>5}  {p1:>2}  {p2:>2}  {p3:>2}  {expl:>4}  {ok_flag}")


def main():
    mode = "DRY RUN" if DRY else "LIVE"
    print(f"=== cleanup_db.py [{mode}] ===\n")

    db.init_pool()
    with db.get_conn() as conn:
        print("── Bước 1: Xóa exam duplicate ──────────────────────────────────────────")
        step1_delete_duplicate_exams(conn)

        print("\n── Bước 2: Dọn tu_luan (dedup + trim >207) ────────────────────────────")
        step2_fix_tu_luan(conn)

        print("\n── Bước 3: Tổng quan các exam mới sau cleanup ─────────────────────────")
        step3_show_summary(conn)

    print("\nHoàn tất.")


if __name__ == "__main__":
    main()
