import sys
from database.db import supabase

exam_id = 89
print(f"Fetching questions for exam {exam_id}")
try:
    response = supabase.table("questions").select("*").eq("exam_id", exam_id).execute()
    for q in response.data:
        if "3^{x-2}" in q.get("content", "") or "Câu 12" in q.get("content", ""):
            print(f"Found question: {q['id']}")
            print(repr(q["content"]))
            
            # also print options
            print(repr(q.get("options")))
except Exception as e:
    print("Error:", e)
