"""
Helper functions for SmartQuery-AI nodes
Contains LLM utilities, Athena initialization, and query generation
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import Config
from database.athena_utils import initialize_athena
import json
import pandas as pd
import logging
import os

logger = logging.getLogger(__name__)

# LLM Singleton instances to avoid recreating clients
_chatbot_instance = None
_chart_llm_instance = None
_athena_initialized = False


def get_chatbot() -> ChatOpenAI:
    """Get or create chatbot instance (singleton)"""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = ChatOpenAI(
            model=Config.MODEL_NAME,
            api_key=Config.OPENAI_API_KEY,
            temperature=Config.TEMPERATURE
        )
    return _chatbot_instance


def get_chart_llm() -> ChatOpenAI:
    """Get or create chart LLM instance (singleton)"""
    global _chart_llm_instance
    if _chart_llm_instance is None:
        _chart_llm_instance = ChatOpenAI(
            model=Config.MODEL_NAME,
            api_key=Config.OPENAI_API_KEY,
            temperature=0
        )
    return _chart_llm_instance


def initialize_athena_connection() -> None:
    """
    Initialize AWS Athena connection on first use
    
    Raises:
        ValueError: If required AWS configuration is missing
    """
    global _athena_initialized
    
    if not _athena_initialized:
        if not all([Config.AWS_ACCESS_KEY_ID, Config.AWS_SECRET_ACCESS_KEY, 
                   Config.ATHENA_S3_OUTPUT_LOCATION, Config.ATHENA_DATABASE]):
            raise ValueError(
                "Missing AWS Athena configuration. Please set the following environment variables: "
                "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, ATHENA_S3_OUTPUT_LOCATION, ATHENA_DATABASE"
            )
        
        initialize_athena(
            aws_access_key=Config.AWS_ACCESS_KEY_ID,
            aws_secret_key=Config.AWS_SECRET_ACCESS_KEY,
            aws_region=Config.AWS_REGION,
            s3_output_location=Config.ATHENA_S3_OUTPUT_LOCATION,
            database=Config.ATHENA_DATABASE,
            workgroup=Config.ATHENA_WORKGROUP
        )
        _athena_initialized = True
        logger.info("Athena connection initialized successfully")


def generate_sql_query_from_user_input(user_question: str) -> str:
    """ Generate SQL query from user's natural language question using LLM """
    
    system_prompt = f"""You are an expert SQL query generator for Amazon Athena.

You have access to the following table schema:

TABLE: sample_data.cancer_patients_csv
DATABASE: sample_data (AWS Athena - AwsDataCatalog)

SCHEMA:
| Column          | Type   | Description                                      |
|-----------------|--------|--------------------------------------------------|
| patient_id      | STRING | Unique patient identifier (e.g. P001)            |
| age             | BIGINT | Patient age in years                             |
| gender          | STRING | Male or Female                                   |
| cancer_type     | STRING | Type of cancer: Lung, Breast, Colon, Prostate, Ovarian |
| stage           | STRING | Cancer stage: I, II, III, IV                     |
| tumor_size_cm   | DOUBLE | Tumor size in centimeters                        |
| treatment       | STRING | Treatment type: Chemotherapy, Radiation, Surgery, Hormone Therapy |
| survival_months | BIGINT | Number of months patient survived                |
| smoker          | STRING | Yes or No                                        |
| outcome         | STRING | Survived or Deceased                             |

RULES:
1. Always use the full table name: sample_data.cancer_patients_csv
2. Use standard SQL compatible with Amazon Athena (Presto SQL)
3. Always use LIMIT 100 unless the user specifies otherwise
4. Column names should be wrapped in double quotes if they have special characters
5. For aggregations always include GROUP BY
6. Return ONLY the SQL query, no explanation unless asked
7. Use COUNT(*), AVG(), MIN(), MAX() for analytics queries
8. For visualization queries, always include label column + numeric column
9. When the user mentions SPECIFIC categories (e.g. "male vs female",
   "survived vs deceased", "lung vs breast cancer"), ALWAYS add a WHERE clause
   to filter only those values. Example: WHERE LOWER(gender) IN ('male', 'female')
10. Always exclude NULL values from results unless the user explicitly asks about them.
    Add "AND column IS NOT NULL" to WHERE clause.
11. Use LOWER() for string comparisons to handle inconsistent casing in data.
12. Data may contain dirty/unexpected values — only return rows that match
    the user's intent, not every distinct value in the column.

USER REQUEST: {user_question}

Generate the Athena SQL query:"""
    user_prompt = f"User question: {user_question}"
        
    llm = get_chatbot()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    sql_query = response.content.strip()

    return sql_query


def generate_chart_config_with_llm(df: pd.DataFrame, user_question: str = "") -> dict:
    """
    Use LLM to intelligently format data for visualization
    
    Args:
        df: DataFrame with query results
        user_question: Original user question for context
        
    Returns:
        Dictionary with chart configuration including:
        - chart_type: Type of chart to display
        - title: Chart title
        - columns: Columns to display
        - data: Data rows
    """
    columns = df.columns.tolist()
    data = df.values.tolist()
    num_rows = len(df)
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    sample_data = df.head(5).to_dict('records')
    
    # Identify column types
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    system_prompt = """You are a data visualization expert. Analyze data and choose the BEST chart type.

Available chart types:
- "pie": Parts of a whole (2-10 categories, shows proportions)
- "bar": Compare values across categories (vertical bars)
- "bar_horizontal": Compare many categories (horizontal bars, better for 10+ items)
- "line": Trends over time or continuous sequence
- "scatter": Relationship between two numeric variables
- "area": Cumulative trends over time
- "table": Complex data or default fallback

Rules:
1. Pie chart: Only for 2-10 categories with proportional data
2. Bar chart: Comparing categorical values
3. Line chart: Time series or sequential data
4. Scatter: Correlation between numeric variables (need 10+ points)
5. Consider what insight is most valuable

Respond with ONLY valid JSON (no markdown, no backticks, no explanation):
{
  "chart_type": "one of the types above",
  "title": "clear descriptive title",
  "columns": ["column names to use"],
  "data": [["row1"], ["row2"]]
}"""
    
    user_prompt = f"""User question: "{user_question}"

Data to visualize:
- Columns: {columns}
- Data types: {dtypes}
- Row count: {num_rows}
- Numeric columns: {numeric_cols}
- Categorical columns: {categorical_cols}

Sample rows:
{json.dumps(sample_data, indent=2, default=str)}

Full dataset:
{json.dumps({'columns': columns, 'data': data[:20]}, default=str)}

Choose the BEST chart type and format. Return ONLY JSON."""

    llm = get_chart_llm()
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    # Clean and parse response
    response_text = response.content.strip()
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    chart_config = json.loads(response_text)
    
    # Validate and set defaults
    chart_config.setdefault('chart_type', 'table')
    chart_config.setdefault('title', 'Data Visualization')
    chart_config.setdefault('columns', columns)
    chart_config.setdefault('data', data)
    
    logger.info(f"✅ LLM chose chart type: {chart_config['chart_type']}")
    
    return chart_config
