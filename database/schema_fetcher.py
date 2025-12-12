"""
Fetch schema dynamically from AWS Glue
No hardcoding!
"""
import boto3
from typing import Dict, List
from config import Config
import json

_cached_schema = None


def get_glue_schema() -> Dict:
    """
    Fetch table schema from AWS Glue catalog
    Cache it to avoid repeated API calls
    """
    global _cached_schema
    
    if _cached_schema is not None:
        return _cached_schema
    
    try:
        glue_client = boto3.client(
            'glue',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        
        # Get all tables in database
        response = glue_client.get_tables(DatabaseName=Config.GLUE_DATABASE_NAME)
        
        tables_info = {}
        
        for table in response['TableList']:
            table_name = table['Name']
            columns = []
            
            for col in table['StorageDescriptor']['Columns']:
                columns.append({
                    'name': col['Name'],
                    'type': col['Type'],
                    'comment': col.get('Comment', '')
                })
            
            tables_info[table_name] = {
                'columns': columns,
                'location': table['StorageDescriptor'].get('Location', ''),
                'input_format': table['StorageDescriptor'].get('InputFormat', '')
            }
        
        _cached_schema = tables_info
        print(f" Loaded schema for {len(tables_info)} tables from Glue")
        return tables_info
        
    except Exception as e:
        print(f" Error fetching Glue schema: {e}")
        return {}


def get_schema_prompt() -> str:
    """
    Generate schema description for LLM prompts
    Returns formatted string describing all tables and columns
    """
    schema = get_glue_schema()
    
    if not schema:
        return "Schema information not available."
    
    prompt_parts = ["DATABASE SCHEMA:\n"]
    
    for table_name, table_info in schema.items():
        prompt_parts.append(f"\nTable: {table_name}")
        prompt_parts.append("Columns:")
        
        for col in table_info['columns']:
            col_name = col['name']
            col_type = col['type']
            col_comment = col['comment']
            
            # Map Glue types to readable descriptions
            type_desc = map_glue_type(col_type)
            
            line = f"  - {col_name} ({type_desc})"
            if col_comment:
                line += f" - {col_comment}"
            
            prompt_parts.append(line)
    
    return "\n".join(prompt_parts)


def map_glue_type(glue_type: str) -> str:
    """
    Map Glue data types to human-readable descriptions
    """
    type_mapping = {
        'int': 'integer',
        'bigint': 'integer',
        'double': 'float/decimal',
        'float': 'float/decimal',
        'string': 'text',
        'varchar': 'text',
        'date': 'date (YYYY-MM-DD)',
        'timestamp': 'timestamp',
        'boolean': 'true/false'
    }
    
    return type_mapping.get(glue_type.lower(), glue_type)


def get_table_sample_values(table_name: str = 'products', limit: int = 5) -> Dict:
    """
    Get sample values from table to show LLM what data looks like
    This helps LLM understand the actual content
    """
    from database.athena_client import run_athena_query
    
    try:
        sql = f"SELECT * FROM {table_name} LIMIT {limit}"
        result = run_athena_query(sql)
        return result
    except Exception as e:
        print(f" Could not fetch sample data: {e}")
        return None


def refresh_schema():
    """
    Force refresh schema cache
    Call this if you update your Glue tables
    """
    global _cached_schema
    _cached_schema = None
    return get_glue_schema()