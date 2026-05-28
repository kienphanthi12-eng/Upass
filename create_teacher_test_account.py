"""
Create a teacher test account via Supabase API
Run: python create_teacher_test_account.py
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(dotenv_path='web/.env.local')

# Supabase config
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in web/.env.local")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Teacher credentials
TEACHER_EMAIL = "teacher.test@thptkimngoc.edu.vn"
TEACHER_PASSWORD = "Test@123456"
TEACHER_NAME = "Giáo Viên Test"

print("=" * 60)
print("👨‍🏫 CREATE TEACHER TEST ACCOUNT")
print("=" * 60)

# Step 1: Create auth user
print(f"\n📧 Creating auth user: {TEACHER_EMAIL}")
try:
    auth_response = supabase.auth.admin.create_user({
        "email": TEACHER_EMAIL,
        "password": TEACHER_PASSWORD,
        "email_confirm": True,  # Skip email confirmation
        "user_metadata": {
            "full_name": TEACHER_NAME,
            "role": "teacher"
        }
    })
    
    user_id = auth_response.user.id
    print(f"✅ Auth user created: {user_id}")
    
except Exception as e:
    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
        print(f"⚠️  User already exists, fetching user ID...")
        # Get existing user
        users_response = supabase.auth.admin.list_users()
        user = next((u for u in users_response.users if u.email == TEACHER_EMAIL), None)
        if user:
            user_id = user.id
            print(f"✅ Found existing user: {user_id}")
        else:
            print(f"❌ Error: User not found in list")
            exit(1)
    else:
        print(f"❌ Error creating auth user: {e}")
        exit(1)

# Step 2: Create teacher record
print(f"\n👨‍🏫 Creating teacher record...")
try:
    # Check if teacher already exists
    existing = supabase.table("teachers").select("id").eq("id", user_id).execute()
    
    if existing.data:
        print(f"⚠️  Teacher record already exists for user {user_id}")
    else:
        teacher_data = {
            "id": user_id,
            "full_name": TEACHER_NAME,
            "email": TEACHER_EMAIL
        }
        
        supabase.table("teachers").insert(teacher_data).execute()
        print(f"✅ Teacher record created successfully!")

except Exception as e:
    print(f"❌ Error creating teacher record: {e}")
    exit(1)

# Step 3: Summary
print("\n" + "=" * 60)
print("✅ TEACHER ACCOUNT CREATED SUCCESSFULLY!")
print("=" * 60)
print(f"\n📧 Email:    {TEACHER_EMAIL}")
print(f"🔑 Password: {TEACHER_PASSWORD}")
print(f"👤 Name:     {TEACHER_NAME}")
print(f"\n🌐 Login URL: http://localhost:3000/login")
print(f"📊 Dashboard: http://localhost:3000/teacher/dashboard")
print("\n⚠️  Remember to:")
print("   1. Run migrations: web/supabase/001_teacher_ocr.sql")
print("   2. Run migrations: web/supabase/002_teacher_editor.sql")
print("   3. Start dev server: cd web && npm run dev")
print("=" * 60)
