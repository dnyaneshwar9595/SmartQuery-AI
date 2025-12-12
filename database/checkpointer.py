# from langgraph.checkpoint.postgres import PostgresSaver
# from config import Config

# class CheckpointerManager:
#     """Manage checkpointer connection lifecycle"""
#     def __init__(self):
#         self._connection = None
#         self._checkpointer = None
    
#     def get_checkpointer(self):
#         if self._checkpointer is None:
#             self._connection = PostgresSaver.from_conn_string(Config.DB_URI)
#             self._checkpointer = self._connection.__enter__()
#         return self._checkpointer
    
#     def close(self):
#         if self._connection is not None:
#             self._connection.__exit__(None, None, None)
#             self._connection = None
#             self._checkpointer = None

# # Global instance
# _manager = CheckpointerManager()

# def get_checkpointer():
#     """Get checkpointer instance"""
#     return _manager.get_checkpointer()

"""
Fixed checkpointer with proper connection handling
"""
from langgraph.checkpoint.postgres import PostgresSaver
from config import Config
import psycopg2

_checkpointer = None

def get_checkpointer():
    """
    Get or create PostgresSaver instance
    Uses singleton pattern
    """
    global _checkpointer
    
    if _checkpointer is None:
        print("🔌 Connecting to PostgreSQL checkpointer...")
        
        try:
            # Create connection using psycopg2
            conn = psycopg2.connect(Config.DB_URI)
            
            # Create PostgresSaver with the connection
            _checkpointer = PostgresSaver(conn)
            
            # Setup tables if needed
            _checkpointer.setup()
            
            print(" Checkpointer connected\n")
            
        except Exception as e:
            print(f" Checkpointer connection failed: {e}")
            print("Run: python database/setup_checkpoints.py")
            raise
    
    return _checkpointer


def close_checkpointer():
    """
    Close checkpointer connection
    Call this on app shutdown if needed
    """
    global _checkpointer
    if _checkpointer is not None:
        try:
            _checkpointer.conn.close()
            print("Checkpointer connection closed")
        except:
            pass
        _checkpointer = None