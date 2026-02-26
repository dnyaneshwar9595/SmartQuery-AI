"""
tools.py — Capabilities that agents can call autonomously.
──────────────────────────────────────────────────────────────
Each @tool function is a self-contained action.  The create_agent
ReAct agents decide WHICH tool to call and in WHAT order.

Tools are grouped by agent:
  DATA_AGENT_TOOLS     → generate_sql, validate_sql, execute_sql
  VIZ_AGENT_TOOLS      → create_chart_config, modify_chart_type
  ANALYSIS_AGENT_TOOLS → analyze_data
"""

from langchain_core.tools import tool
from database.athena_utils import execute_athena_query, validate_query
from core.helpers import (
    initialize_athena_connection,
    generate_sql_query_from_user_input,
    generate_chart_config_with_llm,
)
import pandas as pd
import json


# ─────────────────────── DATA TOOLS ───────────────────────

@tool
def generate_sql(user_question: str) -> str:
    """Turn a natural-language question into a SQL query for AWS Athena."""
    try:
        initialize_athena_connection()
        sql = generate_sql_query_from_user_input(user_question)
        # Strip markdown fencing the LLM sometimes adds
        return sql.strip("`").replace("```", "").replace("sql", "", 1).strip()
    except Exception as e:
        return f"ERROR: {e}"


@tool
def validate_sql(sql_query: str) -> str:
    """Check that a SQL query is safe (SELECT only). Returns 'VALID' or why it failed."""
    if validate_query(sql_query):
        return "VALID"
    return "INVALID: Only SELECT allowed. No DROP/DELETE/INSERT/UPDATE/ALTER/CREATE/TRUNCATE."


@tool
def execute_sql(sql_query: str) -> str:
    """Run a validated SQL query on Athena.  Returns JSON with 'columns' and 'data'."""
    try:
        initialize_athena_connection()
        results = execute_athena_query(sql_query)
        return json.dumps(results, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ──────────────────── VISUALIZATION TOOLS ─────────────────

@tool
def create_chart_config(query_results_json: str, user_question: str) -> str:
    """Build a Plotly chart config from query results + user intent."""
    try:
        qr = json.loads(query_results_json)
        if "error" in qr:
            return json.dumps({"error": qr["error"]})
        df = pd.DataFrame(qr["data"], columns=qr["columns"])
        config = generate_chart_config_with_llm(df, user_question)
        return json.dumps(config, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def modify_chart_type(current_chart_config_json: str, new_chart_type: str) -> str:
    """Swap the chart type (pie / bar / line / scatter / area / table / bar_horizontal)."""
    valid_types = ["pie", "bar", "bar_horizontal", "line", "scatter", "area", "table"]
    if new_chart_type not in valid_types:
        return json.dumps({"error": f"Pick one of: {', '.join(valid_types)}"})
    try:
        config = json.loads(current_chart_config_json)
        config["chart_type"] = new_chart_type
        return json.dumps(config, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ──────────────────── ANALYSIS TOOLS ──────────────────────

@tool
def analyze_data(query_results_json: str, analysis_request: str) -> str:
    """Compute stats (min/max/mean/unique counts) on query results with pandas."""
    try:
        qr = json.loads(query_results_json)
        if "error" in qr:
            return f"Cannot analyze: {qr['error']}"

        df = pd.DataFrame(qr["data"], columns=qr["columns"])
        lines = [
            f"Dataset: {len(df)} rows x {len(df.columns)} columns",
            f"Columns: {', '.join(df.columns.tolist())}",
        ]

        # Numeric stats
        for col in df.select_dtypes(include=["float64", "int64"]).columns:
            lines.append(
                f"  {col}: min={df[col].min()}, max={df[col].max()}, "
                f"mean={df[col].mean():.2f}, median={df[col].median():.2f}"
            )

        # Categorical stats
        for col in df.select_dtypes(include=["object", "category"]).columns:
            n = df[col].nunique()
            lines.append(f"  {col}: {n} unique values")
            if n <= 10:
                lines.append(f"    Distribution: {df[col].value_counts().to_dict()}")

        lines.append(f"\nFirst 5 rows:\n{df.head().to_string()}")
        return "\n".join(lines)
    except Exception as e:
        return f"Analysis failed: {e}"


# ──────────────────── TOOL GROUPS ─────────────────────────
# Each list is handed to one create_agent worker.

DATA_AGENT_TOOLS     = [generate_sql, validate_sql, execute_sql]
VIZ_AGENT_TOOLS      = [create_chart_config, modify_chart_type]
ANALYSIS_AGENT_TOOLS = [analyze_data]
