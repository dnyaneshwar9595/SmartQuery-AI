from database.connection import get_db_connection

def setup_threads_table():
    """Create threads table if it doesn't exist"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_threads (
                thread_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

def save_thread(thread_id: str, title: str):
    """Save a thread to database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_threads (thread_id, title)
            VALUES (%s, %s)
            ON CONFLICT (thread_id) DO NOTHING
        """, (thread_id, title))
        conn.commit()
    finally:
        conn.close()

def load_all_threads():
    """Load all threads from database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT thread_id, title 
            FROM chat_threads 
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()
    finally:
        conn.close()

def delete_thread(thread_id: str):
    """Delete a thread and its checkpoints"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_threads WHERE thread_id = %s", (thread_id,))
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
        conn.commit()
    finally:
        conn.close()

# Initialize table on import
setup_threads_table()