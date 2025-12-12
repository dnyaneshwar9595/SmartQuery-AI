"""
Setup correct PostgreSQL tables for LangGraph checkpointer
Run this ONCE to create/fix the checkpoint tables
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DB_URI directly from environment
DB_URI = os.getenv(
    "DB_URI",
    "postgresql://postgres:Kaustubh%407@localhost:5432/smart_query?sslmode=disable"
)

print(f"Using DB_URI: {DB_URI.split('@')[1] if '@' in DB_URI else DB_URI}\n")

def setup_checkpoint_tables():
    """
    Create the correct checkpoint tables structure for LangGraph
    This matches what PostgresSaver expects
    """
    conn = psycopg2.connect(DB_URI)
    cursor = conn.cursor()
    
    try:
        print("🔧 Setting up checkpoint tables...")
        
        # Drop existing incorrect table if exists
        cursor.execute("DROP TABLE IF EXISTS checkpoints CASCADE")
        print("  ✓ Dropped old checkpoints table")
        
        # Create correct checkpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_ns TEXT NOT NULL DEFAULT '',
                checkpoint_id TEXT NOT NULL,
                parent_checkpoint_id TEXT,
                type TEXT,
                checkpoint JSONB NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
            )
        """)
        print("  ✓ Created checkpoints table with correct schema")
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx 
            ON checkpoints(thread_id)
        """)
        print("  ✓ Created index on thread_id")
        
        # Create writes table for checkpoint writes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoint_writes (
                thread_id TEXT NOT NULL,
                checkpoint_ns TEXT NOT NULL DEFAULT '',
                checkpoint_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                idx INTEGER NOT NULL,
                channel TEXT NOT NULL,
                type TEXT,
                value JSONB,
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
            )
        """)
        print("  ✓ Created checkpoint_writes table")
        
        conn.commit()
        print("✅ Checkpoint tables setup complete!\n")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error setting up tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def verify_checkpoint_schema():
    """
    Verify the checkpoint table has correct schema
    """
    conn = psycopg2.connect(DB_URI)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'checkpoints'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        print("\n📋 Checkpoint table schema:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")
        
        # Check required columns
        required = ['thread_id', 'checkpoint_ns', 'checkpoint_id', 'checkpoint', 'metadata']
        existing = [col[0] for col in columns]
        
        missing = [col for col in required if col not in existing]
        if missing:
            print(f"\n⚠️ Missing columns: {missing}")
            return False
        
        print("\n✅ Schema is correct!")
        return True
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("LANGGRAPH CHECKPOINT TABLE SETUP")
    print("=" * 60 + "\n")
    
    setup_checkpoint_tables()
    verify_checkpoint_schema()
    
    print("\n" + "=" * 60)
    print("✅ Setup complete! You can now run: streamlit run app.py")
    print("=" * 60)