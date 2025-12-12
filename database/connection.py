import psycopg2
from config import Config

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(Config.DB_URI)