import time
import boto3
import pandas as pd
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
DB_NAME = os.getenv("GLUE_DATABASE_NAME")
OUTPUT_LOCATION = os.getenv("ATHENA_OUTPUT_LOCATION")
WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")

athena = boto3.client("athena", region_name=AWS_REGION)


def run_athena_query(sql: str) -> Dict[str, Any]:
    """
    Executes a SQL query on Athena and returns results as JSON.
    """
    print(f"📡 Executing Athena SQL:\n{sql}\n")

    # Start query
    res = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": DB_NAME},
        ResultConfiguration={"OutputLocation": OUTPUT_LOCATION},
        WorkGroup=WORKGROUP,
    )
    qid = res["QueryExecutionId"]

    # Polling
    while True:
        status = athena.get_query_execution(QueryExecutionId=qid)
        state = status["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)

    if state != "SUCCEEDED":
        raise RuntimeError(f"Athena query failed: {state}")

    # Fetch results
    result = athena.get_query_results(QueryExecutionId=qid)
    cols = [c["Name"] for c in result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]

    rows: List[List[Any]] = []
    for r in result["ResultSet"]["Rows"][1:]:
        rows.append([cell.get("VarCharValue") for cell in r["Data"]])

    return {
        "columns": cols,
        "data": rows,
        "dtypes": {c: "string" for c in cols}
    }
