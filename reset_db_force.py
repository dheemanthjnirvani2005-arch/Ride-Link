import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

# Hardcode your DB URL or load from .env manually if preferred
# Based on your previous uploads:
DB_URL = "postgresql://postgres:30324@localhost/uber_demo"

def reset_database():
    print("🔌 Connecting to database...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        print("🗑️  Dropping all tables...")
        # This drops the public schema and recreates it, wiping EVERYTHING
        cur.execute("DROP SCHEMA public CASCADE;")
        cur.execute("CREATE SCHEMA public;")
        cur.execute("GRANT ALL ON SCHEMA public TO postgres;")
        cur.execute("GRANT ALL ON SCHEMA public TO public;")
        
        print("✅ Database wiped successfully.")
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    reset_database()