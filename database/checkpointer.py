from langgraph.checkpoint.postgres import PostgresSaver
from config import Config

class CheckpointerManager:
    """Manage checkpointer connection lifecycle"""
    def __init__(self):
        self._connection = None
        self._checkpointer = None
    
    def get_checkpointer(self):
        if self._checkpointer is None:
            self._connection = PostgresSaver.from_conn_string(Config.DB_URI)
            self._checkpointer = self._connection.__enter__()
        return self._checkpointer
    
    def close(self):
        if self._connection is not None:
            self._connection.__exit__(None, None, None)
            self._connection = None
            self._checkpointer = None

# Global instance
_manager = CheckpointerManager()

def get_checkpointer():
    """Get checkpointer instance"""
    return _manager.get_checkpointer()