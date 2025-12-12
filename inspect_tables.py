from database.connection import get_db_connection

conn = get_db_connection()
try:
    cur = conn.cursor()

    print("\n=== Columns in checkpoints table ===")
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'checkpoints';
    """)
    for row in cur.fetchall():
        print(row)

    print("\n=== Row Count ===")
    cur.execute("SELECT count(*) FROM checkpoints;")
    print("rows:", cur.fetchone()[0])

finally:
    conn.close()
