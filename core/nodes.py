
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
# from config import Config
# from core.state import ChatState
# from utils.dataframe_helper import dict_to_dataframe
# from database.athena_client import run_athena_query
# import json
# import pandas as pd
# from typing import Dict, Any

# # Initialize LLM
# llm = ChatOpenAI(
#     model=Config.MODEL_NAME,
#     api_key=Config.OPENAI_API_KEY,
#     temperature=Config.TEMPERATURE
# )

# # ============================================================================
# # NODE 1: CLASSIFY QUERY INTENT
# # ============================================================================
# def classify_query_node(state: ChatState) -> ChatState:
#     """
#     Determines if the user query requires database access or is general chat.
#     Returns state with 'intent' field: 'db' or 'chat'
#     """
#     messages = state['messages']
#     user_query = messages[-1].content
    
#     system_prompt = """You are a query classifier for a data analytics system.

# DATABASE SCHEMA:
# - Table: products
# - Columns: product_id (int), product_name (text), category (text), brand (text), 
#            price (float), rating (float), date (date)

# Your task: Classify if the user query requires DATABASE ACCESS or is GENERAL CHAT.

# CLASSIFY AS "db" IF:
# - User asks for data, statistics, aggregations, filtering, or analysis
# - Query mentions: select, fetch, show, get, find, analyze, compare, list
# - Examples: "show me sales by category", "top 5 products", "average rating"

# CLASSIFY AS "chat" IF:
# - Greetings, small talk, clarifications
# - Questions about the system capabilities
# - General conversation unrelated to data

# RESPOND WITH ONLY ONE WORD: "db" or "chat"
# """
    
#     try:
#         response = llm.invoke([
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=f"User query: {user_query}")
#         ])
        
#         intent = response.content.strip().lower()
        
#         # Validate response
#         if intent not in ['db', 'chat']:
#             print(f" Invalid intent '{intent}', defaulting to 'chat'")
#             intent = 'chat'
        
#         print(f" Query classified as: {intent}")
        
#         return {
#             'intent': intent,
#             'messages': messages
#         }
        
#     except Exception as e:
#         print(f" Classification error: {e}")
#         return {
#             'intent': 'chat',  # Safe default
#             'messages': messages
#         }

# # ============================================================================
# # NODE 2: GENERATE SQL FROM NATURAL LANGUAGE
# # ============================================================================
# def generate_sql_node(state: ChatState) -> ChatState:
#     """
#     Converts natural language query to SQL using LLM with detailed schema context.
#     Returns state with 'sql_query' field.
#     """
#     messages = state['messages']
#     user_query = messages[-1].content
    
#     system_prompt = """You are an expert SQL query generator for AWS Athena.

# DATABASE SCHEMA:
# Table: products
# Columns:
# - product_id (INT) - Unique product identifier
# - product_name (VARCHAR) - Full product name
# - category (VARCHAR) - Product category (Clothing, Electronics, Sports, Groceries, etc.)
# - brand (VARCHAR) - Brand name
# - price (DOUBLE) - Product price in USD
# - rating (DOUBLE) - Customer rating (0.0 to 5.0)
# - date (DATE) - Transaction/record date

# IMPORTANT RULES:
# 1. Generate ONLY valid Athena SQL (Presto SQL dialect)
# 2. Always use lowercase table/column names
# 3. Use proper aggregations: SUM(), AVG(), COUNT(), MIN(), MAX()
# 4. For grouping: Always include GROUP BY with aggregate functions
# 5. For sorting: Use ORDER BY (default DESC for rankings)
# 6. Limit results to 100 rows max (use LIMIT clause)
# 7. Use CAST() for type conversions
# 8. Date filters: Use DATE column with format 'YYYY-MM-DD'

# COMMON PATTERNS:
# - "top N" → ORDER BY ... DESC LIMIT N
# - "average/mean" → AVG(column)
# - "total/sum" → SUM(column)
# - "by category" → GROUP BY category
# - "each brand" → GROUP BY brand

# RESPOND WITH:
# - ONLY the SQL query
# - NO explanations, NO markdown, NO backticks
# - Valid executable SQL only

# Example:
# User: "Show me total sales by category"
# Response: SELECT category, SUM(price) as total_sales FROM products GROUP BY category ORDER BY total_sales DESC LIMIT 100
# """
    
#     user_prompt = f"""Generate SQL for this request:
# "{user_query}"

# Remember: Return ONLY executable SQL, nothing else."""
    
#     try:
#         response = llm.invoke([
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=user_prompt)
#         ])
        
#         sql_query = response.content.strip()
        
#         # Clean up common issues
#         sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
#         sql_query = sql_query.replace("\n", " ").strip()
        
#         # Validate SQL starts with SELECT
#         if not sql_query.lower().startswith('select'):
#             raise ValueError(f"Generated SQL doesn't start with SELECT: {sql_query}")
        
#         print(f" Generated SQL:\n{sql_query}\n")
        
#         return {
#             'sql_query': sql_query,
#             'messages': messages
#         }
        
#     except Exception as e:
#         print(f" SQL generation error: {e}")
        
#         # Fallback safe query
#         fallback_sql = "SELECT * FROM products LIMIT 10"
        
#         return {
#             'sql_query': fallback_sql,
#             'messages': messages + [AIMessage(content=f"I had trouble generating SQL. Using fallback query: {fallback_sql}")]
#         }

# # ============================================================================
# # NODE 3: EXECUTE ATHENA QUERY
# # ============================================================================
# def athena_query_node(state: ChatState) -> ChatState:
#     """
#     Executes SQL query on AWS Athena and returns results.
#     Uses direct boto3 client (not MCP in this version for stability).
#     """
#     sql = state.get("sql_query")
#     if not sql:
#         raise ValueError("Missing sql_query in state")

#     print(f" Executing Athena query...")

#     try:
#         # Execute query using boto3 client
#         query_results = run_athena_query(sql)
        
#         # Validate results
#         if not query_results or not query_results.get('columns'):
#             print(" Empty results from Athena")
#             return {
#                 "query_results": None,
#                 "messages": state["messages"] + [
#                     AIMessage(content="Query executed but returned no results.")
#                 ]
#             }
        
#         print(f" Query returned {len(query_results['data'])} rows")
        
#         return {
#             "query_results": query_results,
#             "messages": state["messages"]
#         }
        
#     except Exception as e:
#         print(f" Athena execution error: {e}")
        
#         return {
#             "query_results": None,
#             "messages": state["messages"] + [
#                 AIMessage(content=f"Database query failed: {str(e)}")
#             ]
#         }

# # ============================================================================
# # NODE 4: GENERATE CHART CONFIGURATION
# # ============================================================================
# def chart_config_node(state: ChatState) -> ChatState:
#     """
#     Analyzes query results and generates optimal chart configuration.
#     Uses LLM to intelligently select chart type and formatting.
#     """
#     query_results = state.get('query_results')
    
#     if query_results is None or not query_results.get('data'):
#         return {
#             'chart_config': None,
#             'messages': state['messages']
#         }
    
#     # Convert to DataFrame for analysis
#     df = dict_to_dataframe(query_results)
    
#     if df.empty:
#         return {
#             'chart_config': None,
#             'messages': state['messages']
#         }
    
#     user_question = state['messages'][-1].content
#     chart_config = generate_chart_config_with_llm(df, user_question)
    
#     print(f" Chart type selected: {chart_config.get('chart_type')}")
    
#     return {
#         'chart_config': chart_config,
#         'messages': state['messages']
#     }

# # ============================================================================
# # NODE 5: GENERAL CHAT (NON-DATABASE QUERIES)
# # ============================================================================
# def general_chat_node(state: ChatState) -> ChatState:
#     """
#     Handles non-database queries with conversational AI.
#     """
#     messages = state['messages']
    
#     system_message = SystemMessage(content="""You are a helpful data analytics assistant.

# You help users:
# - Understand available data and capabilities
# - Formulate better queries
# - Interpret results
# - Provide general conversation

# Be concise, friendly, and helpful. If users ask about data, guide them to ask specific questions.""")
    
#     try:
#         response = llm.invoke([system_message] + messages)
        
#         return {
#             'messages': [response],
#             'chart_config': None,
#             'query_results': None
#         }
        
#     except Exception as e:
#         print(f"❌ Chat error: {e}")
#         return {
#             'messages': [AIMessage(content="I'm having trouble responding. Please try again.")],
#             'chart_config': None,
#             'query_results': None
#         }

# # ============================================================================
# # HELPER: LLM-POWERED CHART CONFIGURATION
# # ============================================================================
# def generate_chart_config_with_llm(df: pd.DataFrame, user_question: str = "") -> Dict[str, Any]:
#     """
#     Uses LLM to analyze data and select optimal visualization.
    
#     Returns:
#         dict: Chart configuration with type, title, columns, data
#     """
#     columns = df.columns.tolist()
#     data = df.values.tolist()
#     num_rows = len(df)
#     dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
#     sample_data = df.head(5).to_dict('records')
    
#     # Identify column types
#     numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
#     categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
#     system_prompt = """You are a data visualization expert. Analyze the data and choose the BEST chart type.

# AVAILABLE CHART TYPES:
# 1. "pie" - Parts of a whole (2-10 categories, shows proportions)
#    Use when: Single categorical + single numeric, showing composition
   
# 2. "bar" - Compare values across categories (vertical bars)
#    Use when: Comparing categorical data, < 10 categories
   
# 3. "bar_horizontal" - Compare many categories (horizontal bars)
#    Use when: 10+ categories OR long category names
   
# 4. "line" - Trends over time or continuous sequence
#    Use when: Time series, sequential data, showing trends
   
# 5. "scatter" - Relationship between two numeric variables
#    Use when: 2+ numeric columns, correlation analysis, needs 10+ points
   
# 6. "area" - Cumulative trends over time
#    Use when: Time series showing accumulation
   
# 7. "table" - Complex data or default fallback
#    Use when: Mixed data types, detailed view needed, no clear viz pattern

# SELECTION RULES:
# - Prioritize insight value: What story does the data tell?
# - Consider data size: 2-10 items → pie/bar, 10+ → horizontal bar/table
# - Time/sequence data → line/area chart
# - Correlation/distribution → scatter
# - Default to table if unsure

# RESPOND WITH ONLY VALID JSON (no markdown, no backticks):
# {
#   "chart_type": "one of the 7 types above",
#   "title": "clear, descriptive title",
#   "columns": ["exact column names to visualize"],
#   "data": [["row1_val1", "row1_val2"], ["row2_val1", "row2_val2"]]
# }"""
    
#     user_prompt = f"""User asked: "{user_question}"

# DATA ANALYSIS:
# - Columns: {columns}
# - Data types: {dtypes}
# - Row count: {num_rows}
# - Numeric columns: {numeric_cols}
# - Categorical columns: {categorical_cols}

# SAMPLE DATA (first 5 rows):
# {json.dumps(sample_data, indent=2, default=str)}

# FULL DATASET (up to 20 rows):
# {json.dumps({'columns': columns, 'data': data[:20]}, default=str)}

# Task: Choose the BEST chart type for this data and return ONLY the JSON configuration."""

#     try:
#         response = llm.invoke([
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=user_prompt)
#         ])
        
#         # Clean and parse response
#         response_text = response.content.strip()
#         response_text = response_text.replace("```json", "").replace("```", "").strip()
        
#         chart_config = json.loads(response_text)
        
#         # Validate and set defaults
#         valid_chart_types = ['pie', 'bar', 'bar_horizontal', 'line', 'scatter', 'area', 'table']
#         if chart_config.get('chart_type') not in valid_chart_types:
#             chart_config['chart_type'] = 'table'
        
#         chart_config.setdefault('title', 'Data Visualization')
#         chart_config.setdefault('columns', columns)
#         chart_config.setdefault('data', data)
        
#         print(f" Chart configuration generated: {chart_config['chart_type']}")
        
#         return chart_config
        
#     except Exception as e:
#         print(f" Chart config generation error: {e}")
        
#         # Intelligent fallback based on data shape
#         if len(categorical_cols) == 1 and len(numeric_cols) == 1 and num_rows <= 10:
#             chart_type = "pie"
#         elif len(numeric_cols) >= 2 and num_rows >= 10:
#             chart_type = "scatter"
#         elif num_rows > 10:
#             chart_type = "bar_horizontal"
#         else:
#             chart_type = "table"
        
#         return {
#             "chart_type": chart_type,
#             "title": "Query Results",
#             "columns": columns,
#             "data": data
#         }

"""
Core nodes with:
1. Dynamic schema from Glue (not hardcoded)
2. Full conversation memory (LLM sees all previous messages)
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from config import Config
from core.state import ChatState
from database.athena_client import run_athena_query
from database.schema_fetcher import get_schema_prompt, get_table_sample_values
from utils.dataframe_helper import dict_to_dataframe
import json
import pandas as pd

# Initialize LLM
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    temperature=Config.TEMPERATURE
)


def build_conversation_context(messages: list, max_history: int = 10) -> str:
    """
    Build conversation context from message history
    LLM will see previous questions and answers
    """
    if len(messages) <= 1:
        return "This is the first message in the conversation."
    
    # Get last N messages (excluding current one)
    history = messages[-(max_history + 1):-1]
    
    context_lines = ["Previous conversation:"]
    
    for msg in history:
        if isinstance(msg, HumanMessage):
            context_lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Only show summary, not full response
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            context_lines.append(f"Assistant: {content}")
    
    return "\n".join(context_lines)


# ============================================================================
# NODE 1: CLASSIFY USER INTENT
# ============================================================================
def classify_query_node(state: ChatState) -> ChatState:
    """
    First LLM call: Understand user intent
    - Has conversation memory
    - Knows database schema
    """
    messages = state['messages']
    user_query = messages[-1].content
    
    # Get conversation context
    conversation_context = build_conversation_context(messages)
    
    # Get schema dynamically
    schema_info = get_schema_prompt()
    
    system_prompt = f"""You are a query classifier for a data analytics system.

{schema_info}

YOUR TASK: Classify if user wants to query the database or just chat.

CLASSIFY AS "db" IF user wants:
- View/fetch/show data
- Aggregations (total, average, count, sum)
- Filtering (where conditions)
- Comparisons (top N, compare brands, etc.)
- Analysis (trends, correlations)
- Follow-up questions about previous results (e.g., "show me more details", "what about category X")
- ANY question requiring data from the table

CLASSIFY AS "chat" IF user:
- Greets ("hi", "hello")
- Asks about system capabilities
- General conversation
- Clarifying questions NOT needing data

IMPORTANT: 
- If user refers to previous results ("show me more", "what about X"), classify as "db"
- When in doubt, classify as "db"

RESPOND WITH ONLY ONE WORD: "db" or "chat"
No explanation."""

    user_prompt = f"""{conversation_context}

Current query: "{user_query}"

Classification:"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        intent = response.content.strip().lower()
        
        if intent not in ['db', 'chat']:
            print(f" Invalid intent '{intent}', defaulting to 'chat'")
            intent = 'chat'
        
        print(f" Classification: {intent.upper()}")
        
        return {
            'intent': intent,
            'messages': state['messages']
        }
        
    except Exception as e:
        print(f" Classification error: {e}")
        return {
            'intent': 'chat',
            'messages': state['messages']
        }


# ============================================================================
# NODE 2: GENERATE SQL QUERY
# ============================================================================
def generate_sql_node(state: ChatState) -> ChatState:
    """
    Second LLM call: Convert natural language to SQL
    - Uses dynamic schema
    - Has full conversation memory
    - Can reference previous queries
    """
    messages = state['messages']
    user_query = messages[-1].content
    
    # Get conversation context WITH previous SQL queries
    conversation_context = build_sql_conversation_context(state)
    
    # Get schema dynamically
    schema_info = get_schema_prompt()
    
    # Get sample data to show LLM what the data looks like
    sample_data_info = get_sample_data_description()
    
    system_prompt = f"""You are an expert SQL generator for AWS Athena (Presto SQL dialect).

{schema_info}

{sample_data_info}

ATHENA SQL RULES:
1. Use lowercase for table and column names
2. Aggregations: SUM(), AVG(), COUNT(), MIN(), MAX()
3. Always use GROUP BY with aggregates
4. Sorting: ORDER BY (DESC for top, ASC for bottom)
5. Always add LIMIT (default 100)
6. Dates: Use date column with 'YYYY-MM-DD' format
7. String matching: Use LOWER(column) LIKE LOWER('%pattern%')
8. SELECT only - no DROP, DELETE, INSERT, UPDATE

COMMON PATTERNS:
- "top N" → ORDER BY ... DESC LIMIT N
- "bottom N" → ORDER BY ... ASC LIMIT N
- "average" → AVG(column)
- "total" → SUM(column)
- "by category" → GROUP BY category
- "count" → COUNT(*) or COUNT(DISTINCT column)

IMPORTANT FOR FOLLOW-UP QUESTIONS:
- If user asks "show me more details" → expand previous query
- If user asks "what about X" → modify previous query with new filter
- If user asks "for category Y" → add WHERE category = 'Y'

RESPOND WITH:
- ONLY the SQL query
- NO explanations, NO markdown, NO backticks
- Must be executable"""

    user_prompt = f"""{conversation_context}

Current request: "{user_query}"

SQL:"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        sql_query = response.content.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        sql_query = ' '.join(sql_query.split())
        
        if not sql_query.lower().startswith('select'):
            raise ValueError(f"Invalid SQL: {sql_query}")
        
        # Security check
        dangerous = ['drop', 'delete', 'truncate', 'insert', 'update', 'alter', 'create']
        sql_lower = sql_query.lower()
        for word in dangerous:
            if word in sql_lower:
                raise ValueError(f"Dangerous keyword '{word}' not allowed")
        
        print(f" Generated SQL:\n{sql_query}\n")
        
        return {
            'sql_query': sql_query,
            'messages': state['messages']
        }
        
    except Exception as e:
        print(f" SQL generation error: {e}")
        error_msg = AIMessage(content=f"I had trouble generating SQL: {str(e)}")
        return {
            'sql_query': None,
            'messages': state['messages'] + [error_msg]
        }


def build_sql_conversation_context(state: ChatState) -> str:
    """
    Build context including previous SQL queries
    This helps LLM understand follow-up questions
    """
    messages = state['messages']
    
    if len(messages) <= 1:
        return "First query in conversation."
    
    context_lines = ["Previous conversation:"]
    
    # Look for previous SQL queries in state history
    # This is a simplified version - in production you'd track this better
    for i, msg in enumerate(messages[:-1]):
        if isinstance(msg, HumanMessage):
            context_lines.append(f"\nUser: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Show summary
            summary = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
            context_lines.append(f"Assistant: {summary}")
    
    return "\n".join(context_lines)


def get_sample_data_description() -> str:
    """
    Get sample data to help LLM understand the content
    """
    try:
        sample = get_table_sample_values(limit=3)
        if sample and sample.get('data'):
            return f"""
SAMPLE DATA (first 3 rows):
Columns: {', '.join(sample['columns'])}
Data: {json.dumps(sample['data'][:3], default=str)}
"""
    except:
        pass
    
    return ""


# ============================================================================
# NODE 3: EXECUTE ATHENA QUERY
# ============================================================================
def athena_query_node(state: ChatState) -> ChatState:
    """Execute SQL on Athena"""
    sql = state.get("sql_query")
    
    if not sql:
        return {
            "query_results": None,
            "messages": state["messages"]
        }
    
    print(f" Executing Athena query...")
    
    try:
        query_results = run_athena_query(sql)
        
        if not query_results or not query_results.get('columns'):
            return {
                "query_results": None,
                "messages": state["messages"] + [
                    AIMessage(content="Query executed but returned no results.")
                ]
            }
        
        print(f" Returned {len(query_results['data'])} rows")
        
        return {
            "query_results": query_results,
            "messages": state["messages"]
        }
        
    except Exception as e:
        print(f" Athena error: {e}")
        return {
            "query_results": None,
            "messages": state["messages"] + [
                AIMessage(content=f"Database error: {str(e)}")
            ]
        }


# ============================================================================
# NODE 4: SUMMARIZE & VISUALIZE
# ============================================================================
def chart_config_node(state: ChatState) -> ChatState:
    """
    Third LLM call: Analyze results and create visualization
    - Summarizes what was found
    - Chooses best chart
    """
    query_results = state.get('query_results')
    
    if not query_results or not query_results.get('data'):
        return {
            'chart_config': None,
            'messages': state['messages']
        }
    
    df = dict_to_dataframe(query_results)
    
    if df.empty:
        return {
            'chart_config': None,
            'messages': state['messages']
        }
    
    # Get user's question
    user_messages = [m for m in state['messages'] if isinstance(m, HumanMessage)]
    user_question = user_messages[-1].content if user_messages else ""
    
    # Generate visualization
    chart_config = generate_chart_config_with_llm(df, user_question)
    
    # Generate summary message
    summary = generate_summary_with_llm(df, user_question, state.get('sql_query'))
    
    print(f" Chart: {chart_config.get('chart_type')}")
    
    return {
        'chart_config': chart_config,
        'messages': state['messages'] + [AIMessage(content=summary)]
    }


def generate_summary_with_llm(df: pd.DataFrame, user_question: str, sql_query: str) -> str:
    """
    Use LLM to generate natural language summary of results
    """
    row_count = len(df)
    columns = df.columns.tolist()
    sample_data = df.head(3).to_dict('records')
    
    system_prompt = """You are a data analyst. Summarize query results in natural language.

Be concise but informative. Include:
- How many results were found
- Key insights from the data
- Any interesting patterns

Keep it 2-3 sentences maximum."""

    user_prompt = f"""User asked: "{user_question}"

SQL executed: {sql_query}

Results: {row_count} rows
Columns: {columns}
Sample data: {json.dumps(sample_data, default=str)}

Summary:"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        return response.content.strip()
    except:
        return f"Found {row_count} results."


# ============================================================================
# NODE 5: GENERAL CHAT
# ============================================================================
def general_chat_node(state: ChatState) -> ChatState:
    """
    Handle non-database queries
    Has full conversation memory
    """
    messages = state['messages']
    schema_info = get_schema_prompt()
    
    system_message = SystemMessage(content=f"""You are a helpful data analytics assistant.

{schema_info}

You can help users:
- Understand available data
- Formulate queries
- Interpret previous results
- Answer general questions

Be friendly and concise.""")
    
    try:
        # Pass full conversation history to LLM
        response = llm.invoke([system_message] + messages)
        
        return {
            'messages': [response],
            'chart_config': None,
            'query_results': None
        }
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return {
            'messages': [AIMessage(content="I'm having trouble. Please try again.")],
            'chart_config': None,
            'query_results': None
        }


# ============================================================================
# HELPER: CHART CONFIG
# ============================================================================
def generate_chart_config_with_llm(df: pd.DataFrame, user_question: str) -> dict:
    """Use LLM to choose visualization"""
    columns = df.columns.tolist()
    data = df.values.tolist()
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    system_prompt = """Data visualization expert.

CHARTS:
1. "pie" - Composition (2-10 categories, 1 numeric)
2. "bar" - Compare categories (< 10 items)
3. "bar_horizontal" - Many categories (10+ items)
4. "line" - Trends over time
5. "scatter" - Two numeric variables
6. "area" - Cumulative trends
7. "table" - Detailed view

Respond ONLY with JSON (no markdown):
{"chart_type": "type", "title": "title", "columns": ["cols"], "data": [["row1"]]}"""

    user_prompt = f"""User: "{user_question}"

Columns: {columns}
Types: {dtypes}
Rows: {len(df)}
Numeric: {numeric_cols}
Categorical: {categorical_cols}

Choose chart:"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        text = response.content.strip().replace("```json", "").replace("```", "")
        chart_config = json.loads(text)
        
        valid = ['pie', 'bar', 'bar_horizontal', 'line', 'scatter', 'area', 'table']
        if chart_config.get('chart_type') not in valid:
            chart_config['chart_type'] = 'table'
        
        chart_config.setdefault('columns', columns)
        chart_config.setdefault('data', data)
        
        return chart_config
    except Exception as e:
        print(f" Chart config error: {e}")
        return {"chart_type": "table", "title": "Results", "columns": columns, "data": data}