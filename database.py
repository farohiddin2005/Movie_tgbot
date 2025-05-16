import psycopg2
from dotenv import load_dotenv
import os
from urllib.parse import urlparse

load_dotenv()

def init_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set! Please check your Railway Variables.")

    print(f"Attempting to connect with DATABASE_URL: {db_url}")
    url = urlparse(db_url)
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            link TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advertisement_channels (
            name TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            link TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("*📊 Database initialized successfully.*")

if __name__ == "__main__":
    init_db()