"""
PostgreSQL-based chat history management
Handles persistent storage and retrieval of conversations
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import Config
import logging

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get a new database connection"""
    try:
        conn = psycopg2.connect(Config.DB_URI)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise


def create_tables():
    """Create threads, messages, and query_pipeline tables if they don't exist"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create threads table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id VARCHAR(255) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create messages table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id SERIAL PRIMARY KEY,
                thread_id VARCHAR(255) NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                chart_config JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_role CHECK (role IN ('user', 'assistant'))
            );
        """)
        
        # Create query_pipeline table to store the full query execution pipeline
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_pipeline (
                pipeline_id SERIAL PRIMARY KEY,
                thread_id VARCHAR(255) NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                user_prompt TEXT NOT NULL,
                sql_query TEXT,
                athena_data JSONB,
                prepared_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes for faster queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_pipeline_thread_id ON query_pipeline(thread_id);
        """)
        
        conn.commit()
        logger.info("Database tables created successfully")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error creating tables: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()


def create_thread(title: str) -> str:
    """
    Create a new conversation thread
    
    Args:
        title: Conversation title (usually first message preview)
        
    Returns:
        thread_id: Unique identifier for the thread
    """
    import uuid
    
    thread_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO threads (thread_id, title, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
        """, (thread_id, title, datetime.now(), datetime.now()))
        
        conn.commit()
        logger.info(f"Thread created: {thread_id}")
        return thread_id
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error creating thread: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()


def save_message(thread_id: str, role: str, content: str, chart_config: Optional[Dict[str, Any]] = None):
    """
    Save a message to a thread
    
    Args:
        thread_id: Thread ID
        role: 'user' or 'assistant'
        content: Message content
        chart_config: Optional chart configuration (as dict)
    """
    import json
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        chart_config_json = json.dumps(chart_config) if chart_config else None
        
        cur.execute("""
            INSERT INTO messages (thread_id, role, content, chart_config, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (thread_id, role, content, chart_config_json, datetime.now()))
        
        # Update thread's updated_at timestamp
        cur.execute("""
            UPDATE threads SET updated_at = %s WHERE thread_id = %s
        """, (datetime.now(), thread_id))
        
        conn.commit()
        logger.info(f"Message saved to thread {thread_id}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error saving message: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()


def load_threads() -> List[Dict[str, Any]]:
    """
    Load all threads ordered by most recent first
    
    Returns:
        List of thread dictionaries with keys: thread_id, title, created_at, updated_at
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT thread_id, title, created_at, updated_at
            FROM threads
            ORDER BY updated_at DESC
        """)
        
        threads = cur.fetchall()
        return [dict(thread) for thread in threads]
    except psycopg2.Error as e:
        logger.error(f"Error loading threads: {str(e)}")
        return []
    finally:
        cur.close()
        conn.close()


def load_messages_by_thread(thread_id: str) -> List[Dict[str, Any]]:
    """
    Load all messages from a specific thread
    
    Args:
        thread_id: Thread ID
        
    Returns:
        List of message dictionaries with keys: role, content, chart_config, created_at
    """
    import json
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT role, content, chart_config, created_at
            FROM messages
            WHERE thread_id = %s
            ORDER BY created_at ASC
        """, (thread_id,))
        
        messages = cur.fetchall()
        result = []
        for msg in messages:
            msg_dict = dict(msg)
            # Parse JSON chart_config if present
            # PostgreSQL JSONB is automatically deserialized to dict by psycopg2
            if msg_dict.get('chart_config'):
                if isinstance(msg_dict['chart_config'], str):
                    try:
                        msg_dict['chart_config'] = json.loads(msg_dict['chart_config'])
                    except json.JSONDecodeError:
                        msg_dict['chart_config'] = None
                # else: it's already a dict from psycopg2's JSONB deserialization
            result.append(msg_dict)
        
        return result
    except psycopg2.Error as e:
        logger.error(f"Error loading messages: {str(e)}")
        return []
    finally:
        cur.close()
        conn.close()


def get_thread_by_id(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific thread by ID
    
    Args:
        thread_id: Thread ID
        
    Returns:
        Thread dictionary or None if not found
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT thread_id, title, created_at, updated_at
            FROM threads
            WHERE thread_id = %s
        """, (thread_id,))
        
        thread = cur.fetchone()
        return dict(thread) if thread else None
    except psycopg2.Error as e:
        logger.error(f"Error getting thread: {str(e)}")
        return None
    finally:
        cur.close()
        conn.close()


def delete_thread(thread_id: str):
    """
    Delete a thread and all its messages
    
    Args:
        thread_id: Thread ID to delete
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Messages will be automatically deleted due to ON DELETE CASCADE
        cur.execute("""
            DELETE FROM threads WHERE thread_id = %s
        """, (thread_id,))
        
        conn.commit()
        logger.info(f"Thread deleted: {thread_id}")
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error deleting thread: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()


def save_query_pipeline(
    thread_id: str,
    user_prompt: str,
    sql_query: Optional[str] = None,
    athena_data: Optional[Dict[str, Any]] = None,
    prepared_data: Optional[Dict[str, Any]] = None
) -> int:
    """
    Save the complete query execution pipeline data.
    
    This stores:
    - User's prompt
    - Generated SQL query
    - Raw data fetched from Athena
    - Data prepared/formatted by the LLM node
    
    Args:
        thread_id: Thread ID this pipeline belongs to
        user_prompt: The user's original question/prompt
        sql_query: The SQL query generated by the LLM
        athena_data: Raw data returned from Athena (dict with 'columns' and 'data' keys)
        prepared_data: Processed/formatted data from the data preparation node
        
    Returns:
        pipeline_id: ID of the saved pipeline record
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        import json
        
        athena_data_json = json.dumps(athena_data) if athena_data else None
        prepared_data_json = json.dumps(prepared_data) if prepared_data else None
        
        cur.execute("""
            INSERT INTO query_pipeline (
                thread_id, user_prompt, sql_query, athena_data, prepared_data, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING pipeline_id
        """, (thread_id, user_prompt, sql_query, athena_data_json, prepared_data_json, datetime.now()))
        
        pipeline_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Query pipeline saved with ID: {pipeline_id} for thread: {thread_id}")
        return pipeline_id
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Error saving query pipeline: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()


def load_query_pipeline(thread_id: str) -> List[Dict[str, Any]]:
    """
    Load all query pipelines for a specific thread.
    
    Args:
        thread_id: Thread ID
        
    Returns:
        List of pipeline records with keys: pipeline_id, user_prompt, sql_query, athena_data, prepared_data, created_at
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT pipeline_id, user_prompt, sql_query, athena_data, prepared_data, created_at
            FROM query_pipeline
            WHERE thread_id = %s
            ORDER BY created_at ASC
        """, (thread_id,))
        
        pipelines = cur.fetchall()
        return [dict(pipeline) for pipeline in pipelines]
    except psycopg2.Error as e:
        logger.error(f"Error loading query pipelines: {str(e)}")
        return []
    finally:
        cur.close()
        conn.close()
