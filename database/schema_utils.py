"""
Database schema utilities for fetching Athena table metadata
Provides schema information to LLM for intelligent SQL query generation
"""

from database.athena_connection import AthenaConnection
from database.athena_utils import get_athena_connection
import logging

logger = logging.getLogger(__name__)


def get_database_schema() -> dict:
    """
    Fetch complete database schema from Athena
    
    Returns:
        Dictionary with structure:
        {
            'tables': {
                'table_name': {
                    'description': 'What this table contains',
                    'columns': {
                        'column_name': {
                            'type': 'int64|object|float64|etc',
                            'nullable': True/False,
                            'description': 'What this column stores'
                        },
                        ...
                    },
                    'sample_row': {...}  # Example row from table
                },
                ...
            }
        }
    """
    connection = get_athena_connection()
    if not connection:
        logger.warning("Athena connection not initialized, returning empty schema")
        return {'tables': {}}
    
    # Get all tables in database
    tables = connection.list_tables()
    schema = {'tables': {}}
    
    for table_name in tables:
        # Get column information
        columns_info = connection.describe_table(table_name)
        columns = {}
        
        for col in columns_info:
            columns[col['name']] = {
                'type': col['type'],
                'description': col.get('comment', '')
            }
        
        # Get sample data from table (first row)
        sample_query = f"SELECT * FROM {connection.database}.{table_name} LIMIT 1"
        sample_result = connection.execute_query(sample_query)
        
        sample_row = None
        if sample_result.get('data') and len(sample_result['data']) > 0:
            sample_row = dict(zip(sample_result['columns'], sample_result['data'][0]))
        
        schema['tables'][table_name] = {
            'columns': columns,
            'sample_row': sample_row,
            'row_count_approx': 'Unknown'  # Could be fetched with COUNT(*)
        }
    
    logger.info(f"Successfully fetched schema for {len(schema['tables'])} tables")
    return schema


def format_schema_for_llm(schema: dict) -> str:
    """
    Format database schema as a readable prompt for LLM
    
    Args:
        schema: Schema dictionary from get_database_schema()
        
    Returns:
        Formatted string describing the database structure
    """
    if not schema.get('tables'):
        return "No tables available in the database."
    
    schema_text = "# Available Database Tables and Schemas\n\n"
    
    for table_name, table_info in schema['tables'].items():
        schema_text += f"## Table: `{table_name}`\n"
        schema_text += "### Columns:\n"
        
        for col_name, col_info in table_info['columns'].items():
            col_type = col_info.get('type', 'unknown')
            col_desc = col_info.get('description', '')
            schema_text += f"- `{col_name}` ({col_type})"
            if col_desc:
                schema_text += f" - {col_desc}"
            schema_text += "\n"
        
        # Add sample data
        if table_info.get('sample_row'):
            schema_text += "\n### Sample Row:\n```\n"
            for key, value in table_info['sample_row'].items():
                schema_text += f"{key}: {value}\n"
            schema_text += "```\n"
        
        schema_text += "\n"
    
    return schema_text


# Global cache for schema
_schema_cache = None
_schema_initialized = False


def get_cached_schema(refresh: bool = False) -> dict:
    """
    Get cached database schema (only fetches once per session)
    
    Args:
        refresh: Force refresh of schema cache
        
    Returns:
        Database schema dictionary
    """
    global _schema_cache, _schema_initialized
    
    if refresh or not _schema_initialized:
        _schema_cache = get_database_schema()
        _schema_initialized = True
        logger.info("Schema cache initialized/refreshed")
    
    return _schema_cache


def clear_schema_cache():
    """Clear the schema cache (use if database schema changes)"""
    global _schema_cache, _schema_initialized
    _schema_cache = None
    _schema_initialized = False
    logger.info("Schema cache cleared")
