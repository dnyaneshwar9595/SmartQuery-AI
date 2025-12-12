# scripts/add_checkpoint_column.py
from database.connection import get_db_connection

def add_column():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        ALTER TABLE checkpoints
        ADD COLUMN IF NOT EXISTS checkpoint JSONB;
        """)
        conn.commit()
        print("checkpoint column added (or already exists)")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
