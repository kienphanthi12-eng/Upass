import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()
from database import db

def main():
    db.init_pool()
    target_ids = [164, 165, 166, 167, 168]
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            # Show exams before deletion
            cur.execute("""
                SELECT id, title, (SELECT COUNT(*) FROM questions WHERE exam_id = exams.id)
                FROM exams
                WHERE id = ANY(%s)
            """, (target_ids,))
            rows = cur.fetchall()
            print("Before deletion:")
            for r in rows:
                print(f"ID: {r[0]} | Qs: {r[2]} | Title: {r[1]}")
                
            # Perform deletion
            print("\nDeleting exams...")
            cur.execute("DELETE FROM exams WHERE id = ANY(%s)", (target_ids,))
            deleted = cur.rowcount
            print(f"Deleted {deleted} exams.")
            
        conn.commit()
    print("Commit complete.")

if __name__ == "__main__":
    main()
