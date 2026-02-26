"""
AWS Athena connection and query execution module
Handles all interactions with AWS Athena for data retrieval
"""

import boto3
import time
import pandas as pd
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AthenaConnection:
    """
    Manages AWS Athena connections and query execution
    """
    
    def __init__(self, 
                 aws_access_key: str,
                 aws_secret_key: str,
                 aws_region: str,
                 s3_output_location: str,
                 database: str,
                 workgroup: str = "primary"):
        """
        Initialize Athena connection
        
        Args:
            aws_access_key: AWS Access Key ID
            aws_secret_key: AWS Secret Access Key
            aws_region: AWS Region (e.g., 'us-east-1')
            s3_output_location: S3 path for query results (e.g., 's3://bucket-name/path/')
            database: Athena database name
            workgroup: Athena workgroup name (default: 'primary')
        """
        self.aws_region = aws_region
        self.s3_output_location = s3_output_location
        self.database = database
        self.workgroup = workgroup
        
        # Initialize Athena client
        self.client = boto3.client(
            'athena',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Initialize S3 client for result retrieval
        self.s3_client = boto3.client(
            's3',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute an Athena query and wait for results
        
        Args:
            query: SQL query string
            
        Returns:
            Dictionary containing query results in standardized format
        """
        # Start query execution
        query_execution_id = self._start_query_execution(query)
        
        # Wait for query to complete
        self._wait_for_query_completion(query_execution_id)
        
        # Get query results
        results = self._get_query_results(query_execution_id)
        
        return results
    
    def _start_query_execution(self, query: str) -> str:
        """
        Start Athena query execution
        
        Args:
            query: SQL query string
            
        Returns:
            Query execution ID
        """
        response = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': self.database},
            ResultConfiguration={'OutputLocation': self.s3_output_location},
            WorkGroup=self.workgroup
        )
        
        query_execution_id = response['QueryExecutionId']
        logger.info(f"Query execution started: {query_execution_id}")
        return query_execution_id
    
    def _wait_for_query_completion(self, query_execution_id: str):
        """
        Wait for Athena query to complete
        
        Args:
            query_execution_id: Query execution ID
            
        Raises:
            Exception: If query fails
        """
        while True:
            response = self.client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                logger.info(f"Query {query_execution_id} completed successfully")
                return
            elif status == 'FAILED':
                failure_reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
                raise Exception(f"Query failed: {failure_reason}")
            elif status == 'CANCELLED':
                raise Exception("Query was cancelled")
            
            # Wait before checking again
            time.sleep(1)
    
    def _get_query_results(self, query_execution_id: str) -> Dict[str, Any]:
        """
        Retrieve query results from Athena
        
        Args:
            query_execution_id: Query execution ID
            
        Returns:
            Dictionary with columns, data, and dtypes
        """
        response = self.client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Extract column names from first row (header)
        rows = response['ResultSet']['Rows']
        if not rows:
            return {
                'columns': [],
                'data': [],
                'dtypes': {}
            }
        
        columns = [col['VarCharValue'] for col in rows[0]['Data']]
        
        # Extract data rows
        data = []
        dtypes = {}
        
        for row in rows[1:]:
            row_data = []
            for idx, col in enumerate(row['Data']):
                value = col.get('VarCharValue', None)
                row_data.append(value)
                
                # Infer data types
                if idx < len(columns):
                    if dtypes.get(columns[idx]) is None:
                        dtypes[columns[idx]] = self._infer_type(value)
            
            if row_data:
                data.append(row_data)
        
        return {
            'columns': columns,
            'data': data,
            'dtypes': dtypes
        }
    
    @staticmethod
    def _infer_type(value: Optional[str]) -> str:
        """
        Infer data type from string value
        
        Args:
            value: String value to infer type from
            
        Returns:
            Type string (e.g., 'int64', 'float64', 'object')
        """
        if value is None or value == '':
            return 'object'
        
        # Try integer
        try:
            int(value)
            return 'int64'
        except (ValueError, TypeError):
            pass
        
        # Try float
        try:
            float(value)
            return 'float64'
        except (ValueError, TypeError):
            pass
        
        # Default to object
        return 'object'
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the database
        
        Returns:
            List of table names
        """
        try:
            query = f"SHOW TABLES IN {self.database}"
            response = self.client.get_query_results(
                QueryExecutionId=self._start_query_execution(query)
            )
            
            tables = []
            rows = response['ResultSet']['Rows']
            for row in rows[1:]:  # Skip header
                table_name = row['Data'][0]['VarCharValue']
                tables.append(table_name)
            
            return tables
            
        except Exception as e:
            logger.error(f"Error listing tables: {str(e)}")
            return []
    
    def describe_table(self, table_name: str) -> List[Dict[str, str]]:
        """
        Get column information for a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        try:
            query = f"DESCRIBE {self.database}.{table_name}"
            response = self.client.get_query_results(
                QueryExecutionId=self._start_query_execution(query)
            )
            
            columns = []
            rows = response['ResultSet']['Rows']
            for row in rows[1:]:  # Skip header
                col_info = {
                    'name': row['Data'][0]['VarCharValue'],
                    'type': row['Data'][1]['VarCharValue'],
                    'comment': row['Data'][2].get('VarCharValue', '') if len(row['Data']) > 2 else ''
                }
                columns.append(col_info)
            
            return columns
            
        except Exception as e:
            logger.error(f"Error describing table: {str(e)}")
            return []
