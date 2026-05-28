import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from database import db; db.init_pool()

with db.get_conn() as conn:
    with conn.cursor() as cur:
        print("Creating table web_analytics if not exists...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS web_analytics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id VARCHAR(255) NOT NULL,
                path VARCHAR(255) NOT NULL,
                referrer VARCHAR(255),
                browser VARCHAR(50),
                os VARCHAR(50),
                device_type VARCHAR(20),
                ip_address VARCHAR(45),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
            );
        """)
        conn.commit()
        print("Table web_analytics created successfully!")
