from database.connection import get_db_connection

def add_and_populate():
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Add column if not exists
        cur.execute("""
        ALTER TABLE checkpoints
        ADD COLUMN IF NOT EXISTS checkpoint_ns TEXT;
        """)

        # Populate from JSONB 'checkpoint' field
        cur.execute("""
        UPDATE checkpoints
        SET checkpoint_ns = COALESCE(
            (checkpoint ->> 'ns'),
            (checkpoint ->> 'checkpoint_ns'),
            (checkpoint ->> 'namespace'),
            ((checkpoint -> 'meta') ->> 'ns'),
            NULL
        )
        WHERE checkpoint IS NOT NULL;
        """)

        conn.commit()
        print("checkpoint_ns column created and populated.")
    finally:
        conn.close()


if __name__ == "__main__":
    add_and_populate()
