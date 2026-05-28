"""
Quick script to create teacher account using Supabase Admin API
"""
import os
from dotenv import load_dotenv

# Load env from web/.env.local
load_dotenv(dotenv_path='web/.env.local')

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("=" * 60)
print("CHECKING SUPABASE CONFIGURATION")
print("=" * 60)
print(f"\nSUPABASE_URL: {SUPABASE_URL}")
print(f"SERVICE_KEY: {SERVICE_KEY[:20]}..." if SERVICE_KEY and len(SERVICE_KEY) > 20 else f"SERVICE_KEY: {SERVICE_KEY}")

if not SERVICE_KEY or SERVICE_KEY == "your_service_role_key_here":
    print("\n❌ ERROR: SUPABASE_SERVICE_ROLE_KEY is not set!")
    print("\n📋 Please do this:")
    print("1. Go to: https://app.supabase.com/project/zabvdgnucfanvbjjgnic/settings/api")
    print("2. Copy the 'service_role' key (secret key)")
    print("3. Open file: web/.env.local")
    print("4. Replace 'your_service_role_key_here' with the actual key")
    print("\nExample:")
    print("SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    exit(1)

print("\n✅ Configuration looks good!")
print("\nNow trying to create teacher account...")
