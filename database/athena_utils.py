"""
Utility functions for AWS Athena query generation and execution
"""

import logging
from typing import Dict, Any, Optional
from database.athena_connection import AthenaConnection

logger = logging.getLogger(__name__)

# Global Athena connection instance
_athena_connection: Optional[AthenaConnection] = None


def initialize_athena(aws_access_key: str,
                     aws_secret_key: str,
                     aws_region: str,
                     s3_output_location: str,
                     database: str,
                     workgroup: str = "primary") -> AthenaConnection:
    """
    Initialize and return Athena connection (singleton pattern)
    
    Args:
        aws_access_key: AWS Access Key ID
        aws_secret_key: AWS Secret Access Key
        aws_region: AWS Region
        s3_output_location: S3 path for query results
        database: Athena database name
        workgroup: Athena workgroup name
        
    Returns:
        AthenaConnection instance
    """
    global _athena_connection
    
    if _athena_connection is None:
        _athena_connection = AthenaConnection(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
            s3_output_location=s3_output_location,
            database=database,
            workgroup=workgroup
        )
        logger.info("Athena connection initialized successfully")
    
    return _athena_connection


def get_athena_connection() -> Optional[AthenaConnection]:
    """
    Get the current Athena connection instance
    
    Returns:
        AthenaConnection instance or None if not initialized
    """
    return _athena_connection


def reset_athena_connection():
    """Reset the Athena connection (useful for testing)"""
    global _athena_connection
    _athena_connection = None


def execute_athena_query(query: str) -> Dict[str, Any]:
    connection = get_athena_connection()
    
    if connection is None:
        raise RuntimeError("Athena connection not initialized. Call initialize_athena() first.")
    
    logger.info(f"Executing Athena query: {query[:100]}...")
    return connection.execute_query(query)


def validate_query(query: str) -> bool:
    """
    LLM-powered autonomous validation of SQL query safety.
    The LLM reasons about the query and uses tool-calling to approve/reject.
    
    Args:
        query: SQL query string
        
    Returns:
        True if query is safe, False otherwise
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_core.tools import tool as make_tool
    from config import Config
    
    # Define validation decision tools
    @make_tool
    def approve_query(reason: str) -> str:
        """Call this if the query is SAFE (SELECT-only, no data modification)."""
        return "APPROVED"
    
    @make_tool
    def reject_query(reason: str) -> str:
        """Call this if the query is UNSAFE (contains DROP/DELETE/INSERT/UPDATE/ALTER/CREATE/TRUNCATE, 
        or is not a valid SQL query, or looks like an error message)."""
        return "REJECTED"
    
    validation_tools = [approve_query, reject_query]
    
    # Build validator LLM with forced tool choice
    llm = ChatOpenAI(model=Config.MODEL_NAME, api_key=Config.OPENAI_API_KEY, temperature=0)
    llm_with_tools = llm.bind_tools(validation_tools, tool_choice="required")
    
    system_prompt = """You are a SQL Safety Validator for AWS Athena.

Analyze the given SQL query and determine if it's SAFE to execute.

APPROVE if:
- It's a valid SELECT query
- It only reads data (no modifications)
- It doesn't contain DROP, DELETE, INSERT, UPDATE, ALTER, CREATE, TRUNCATE

REJECT if:
- It contains any data modification keywords
- It's not valid SQL (error messages, plain text, comments)
- It looks like an LLM error response ("I cannot...", "unable to...", etc.)

Call exactly ONE tool with a brief reason."""
    
    response = llm_with_tools.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Query to validate:\n{query}"),
    ])
    
    # Read the tool call decision
    if response.tool_calls:
        tool_name = response.tool_calls[0]["name"]
        reason = response.tool_calls[0].get("args", {}).get("reason", "")
        
        if tool_name == "approve_query":
            logger.info(f"Query approved: {reason}")
            return True
        else:
            logger.warning(f"Query rejected: {reason}")
            return False
    
    # Fallback if no tool call (shouldn't happen with tool_choice="required")
    logger.warning("Validator returned no tool call — rejecting by default")
    return False
