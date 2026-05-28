# encode_exam_titles.py
"""Encode exam titles for Physics (Ly) and Chemistry (Hoa) subjects.

- Physics exams get a flower name as their display_title.
- Chemistry exams get a fruit name as their display_title.

The script connects to the PostgreSQL database via the existing `db` helper,
fetches the relevant exams, assigns deterministic names from predefined lists,
updates the rows, and prints a short summary.
"""

import sys
import io
import random

# Ensure UTF‑8 output (useful for Vietnamese chars)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Project imports
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from database import db

# Predefined name pools – you can extend them as needed.
FLOWER_NAMES = [
    "Rose",
    "Tulip",
    "Orchid",
    "Lily",
    "Sunflower",
    "Daisy",
    "Lavender",
    "Jasmine",
    "Peony",
    "Magnolia",
]
FRUIT_NAMES = [
    "Apple",
    "Banana",
    "Orange",
    "Mango",
    "Pear",
    "Peach",
    "Grape",
    "Kiwi",
    "Pineapple",
    "Strawberry",
]

def fetch_subject_id(cur, code: str) -> int:
    cur.execute("SELECT id FROM subjects WHERE code = %s", (code,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Subject code '{code}' not found in the database")
    return row[0]

def assign_names(exams, name_pool):
    """Assign a deterministic name from *name_pool* to each exam.
    The assignment is stable across runs because we sort by exam.id.
    """
    assigned = []
    for i, exam in enumerate(sorted(exams, key=lambda e: e[0])):  # exam[0] = id
        name = name_pool[i % len(name_pool)]
        assigned.append((exam[0], name))
    return assigned

def main():
    db.init_pool()
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            # Get subject ids for physics (LY) and chemistry (HOA)
            physics_id = fetch_subject_id(cur, "LY")
            chemistry_id = fetch_subject_id(cur, "HOA")

            # Fetch exams for each subject
            cur.execute("SELECT id, title FROM exams WHERE subject_id = %s", (physics_id,))
            physics_exams = cur.fetchall()
            cur.execute("SELECT id, title FROM exams WHERE subject_id = %s", (chemistry_id,))
            chemistry_exams = cur.fetchall()

            # Assign new display titles
            physics_updates = assign_names(physics_exams, FLOWER_NAMES)
            chemistry_updates = assign_names(chemistry_exams, FRUIT_NAMES)

            # Apply updates
            total_updates = 0
            for exam_id, new_name in physics_updates + chemistry_updates:
                cur.execute(
                    "UPDATE exams SET display_title = %s WHERE id = %s",
                    (new_name, exam_id),
                )
                total_updates += 1

            conn.commit()
            print(f"✅ Updated {total_updates} exam titles.")
            print(f"   • Physics (Ly): {len(physics_updates)} exams → flower names")
            print(f"   • Chemistry (Hoa): {len(chemistry_updates)} exams → fruit names")

if __name__ == "__main__":
    main()
