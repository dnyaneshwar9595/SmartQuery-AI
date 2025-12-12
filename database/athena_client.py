import time
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from config import Config
import logging

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AthenaQueryError(Exception):
    """Custom exception for Athena query errors"""
    pass

class AthenaTimeoutError(Exception):
    """Custom exception for query timeouts"""
    pass

def get_athena_client():
    """
    Create a boto3 Athena client with proper configuration.
    Includes connection validation.
    """
    try:
        session = boto3.Session(
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION,
        )
        client = session.client("athena")
        
        # Validate connection by listing workgroups
        client.list_work_groups(MaxResults=1)
        
        return client
        
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to create Athena client: {e}")
        raise AthenaQueryError(f"AWS connection failed: {str(e)}")

def run_athena_query(
    sql: str,
    timeout_seconds: int = 120,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Execute SQL query on Athena with retry logic and comprehensive error handling.
    
    Args:
        sql: SQL query string
        timeout_seconds: Maximum time to wait for query completion
        max_retries: Number of retry attempts for transient failures
        
    Returns:
        Dict containing:
            - columns: List[str]
            - data: List[List[Any]]
            - dtypes: Dict[str, str]
            - row_count: int
            - execution_time: float
            
    Raises:
        AthenaQueryError: For query execution failures
        AthenaTimeoutError: For query timeouts
    """
    
    logger.info(f"Executing Athena query (timeout={timeout_seconds}s):\n{sql}")
    
    client = get_athena_client()
    
    # Retry logic for transient failures
    for attempt in range(max_retries):
        try:
            return _execute_query_with_timeout(client, sql, timeout_seconds)
            
        except (ClientError, BotoCoreError) as e:
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            
            # Retry on throttling or temporary failures
            if error_code in ['ThrottlingException', 'ServiceUnavailableException'] and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Transient error {error_code}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # Permanent failure
            logger.error(f"Athena query failed: {e}")
            raise AthenaQueryError(f"Query execution failed: {str(e)}")
    
    raise AthenaQueryError("Query failed after all retry attempts")

def _execute_query_with_timeout(
    client,
    sql: str,
    timeout_seconds: int
) -> Dict[str, Any]:
    """
    Internal method to execute query and poll for results.
    """
    start_time = time.time()
    
    # Start query execution
    try:
        start_resp = client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": Config.GLUE_DATABASE_NAME},
            ResultConfiguration={
                "OutputLocation": Config.ATHENA_OUTPUT_LOCATION
            },
            WorkGroup=Config.ATHENA_WORKGROUP,
        )
    except ClientError as e:
        raise AthenaQueryError(f"Failed to start query: {str(e)}")
    
    query_id = start_resp["QueryExecutionId"]
    logger.info(f"Query started with ID: {query_id}")
    
    # Poll for completion
    while True:
        elapsed_time = time.time() - start_time
        
        if elapsed_time > timeout_seconds:
            # Attempt to stop the query
            try:
                client.stop_query_execution(QueryExecutionId=query_id)
            except:
                pass
            raise AthenaTimeoutError(f"Query timed out after {timeout_seconds}s")
        
        try:
            exec_resp = client.get_query_execution(QueryExecutionId=query_id)
        except ClientError as e:
            raise AthenaQueryError(f"Failed to get query status: {str(e)}")
        
        state = exec_resp["QueryExecution"]["Status"]["State"]
        
        if state == "SUCCEEDED":
            break
        elif state in ("FAILED", "CANCELLED"):
            reason = exec_resp["QueryExecution"]["Status"].get("StateChangeReason", "Unknown error")
            raise AthenaQueryError(f"Query {state.lower()}: {reason}")
        
        # Still running, wait before polling again
        time.sleep(min(2, timeout_seconds - elapsed_time))
    
    execution_time = time.time() - start_time
    logger.info(f"Query completed in {execution_time:.2f}s")
    
    # Fetch results
    try:
        results_resp = client.get_query_results(
            QueryExecutionId=query_id,
            MaxResults=1000  # Adjust based on your needs
        )
    except ClientError as e:
        raise AthenaQueryError(f"Failed to retrieve results: {str(e)}")
    
    # Parse results
    return _parse_athena_results(results_resp, execution_time)

def _parse_athena_results(results_resp: Dict, execution_time: float) -> Dict[str, Any]:
    """
    Parse Athena API response into structured format with type conversion.
    """
    cols_meta = results_resp["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
    rows = results_resp["ResultSet"]["Rows"]
    
    # Extract column metadata
    columns = [c["Name"] for c in cols_meta]
    dtypes = {c["Name"]: c["Type"] for c in cols_meta}
    
    # Convert rows (skip header row)
    data: List[List[Any]] = []
    
    for row in rows[1:]:  # Skip first row (header)
        row_values: List[Any] = []
        
        for idx, cell in enumerate(row.get("Data", [])):
            raw_value = cell.get("VarCharValue")
            col_type = cols_meta[idx]["Type"].lower()
            
            # Type conversion
            converted_value = _convert_athena_value(raw_value, col_type)
            row_values.append(converted_value)
        
        data.append(row_values)
    
    return {
        "columns": columns,
        "data": data,
        "dtypes": dtypes,
        "row_count": len(data),
        "execution_time": round(execution_time, 2)
    }

def _convert_athena_value(value: Optional[str], col_type: str) -> Any:
    """
    Convert Athena string values to appropriate Python types.
    
    Athena returns all values as strings, this function converts them based on schema type.
    """
    if value is None or value == '':
        return None
    
    try:
        # Integer types
        if col_type in ('int', 'integer', 'bigint', 'smallint', 'tinyint'):
            return int(value)
        
        # Float types
        elif col_type in ('double', 'float', 'decimal', 'real'):
            return float(value)
        
        # Boolean
        elif col_type == 'boolean':
            return value.lower() in ('true', '1', 'yes')
        
        # Date/timestamp (keep as string for now, convert in DataFrame if needed)
        elif col_type in ('date', 'timestamp'):
            return value
        
        # Default: return as string
        else:
            return value
            
    except (ValueError, TypeError):
        # If conversion fails, return original string
        logger.warning(f"Failed to convert value '{value}' to type {col_type}")
        return value

def validate_sql_query(sql: str) -> bool:
    """
    Basic SQL validation to prevent injection and ensure safe queries.
    
    Returns:
        bool: True if query appears safe, False otherwise
    """
    sql_lower = sql.lower().strip()
    
    # Must be a SELECT query
    if not sql_lower.startswith('select'):
        logger.error("Only SELECT queries are allowed")
        return False
    
    # Block dangerous keywords
    dangerous_keywords = ['drop', 'delete', 'truncate', 'insert', 'update', 'alter', 'create']
    
    for keyword in dangerous_keywords:
        if keyword in sql_lower:
            logger.error(f"Dangerous keyword '{keyword}' detected in query")
            return False
    
    return True

def estimate_query_cost(sql: str) -> Dict[str, Any]:
    """
    Estimate the cost of running an Athena query.
    
    Note: This is a rough estimate. Actual costs depend on data scanned.
    """
    # Athena pricing: $5 per TB scanned
    # This is a placeholder - real implementation would analyze query plan
    
    return {
        "estimated_cost_usd": "< $0.01",
        "note": "Actual cost depends on data scanned"
    }