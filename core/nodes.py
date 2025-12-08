from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from config import Config
from core.state import ChatState
from utils.dataframe_helper import dict_to_dataframe
from database.sample_data import get_dummy_athena_output
import json
import pandas as pd

# Initialize chatbot
chatbot = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    temperature=Config.TEMPERATURE
)

def athena_query_node(state: ChatState) -> ChatState:

    query_results = get_dummy_athena_output()
    return {
        'query_results': query_results,
        'messages': state['messages']
    }

def chart_config_node(state: ChatState) -> ChatState:
    """    
    This node takes the query results and generates chart configuration
    using another LLM to format the output for UI rendering
    """
    query_results = state.get('query_results')
    # print(query_results)
    if query_results is None:
        return {
            'chart_config': None,
            'messages': state['messages']
        }
    
    # Reconstruct DataFrame from serialized format
    df = dict_to_dataframe(query_results)
    
    if df.empty:
        return {
            'chart_config': None,
            'messages': state['messages']
        }
    # Use LLM to determine best chart type and format
    user_question = state['messages'][-1].content
    print(user_question)
    chart_config = generate_chart_config_with_llm(df, user_question)
    # chart_type = chart_config.get('chart_type', 'table')
    
    return {
        'chart_config': chart_config
    }

def general_chat_node(state: ChatState) -> ChatState:
    """
    Handle general conversation (non-database queries)
    """
    messages = state['messages']
    response = chatbot.invoke(messages)
    
    return {
        'messages': [response],
        'chart_config': None,  # Clear old chart
        'query_results': None
    }

def generate_chart_config_with_llm(df: pd.DataFrame, user_question: str = "") -> dict:
    """
    Use LLM to intelligently format data for visualization
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

    try:
        llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            api_key=Config.OPENAI_API_KEY,
            temperature=0
        )
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        print(response)
        # Clean and parse response
        response_text = response.content.strip()
        # print(response_text)
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        chart_config = json.loads(response_text)
        
        # Validate and set defaults
        chart_config.setdefault('chart_type', 'table')
        chart_config.setdefault('title', 'Data Visualization')
        chart_config.setdefault('columns', columns)
        chart_config.setdefault('data', data)
        
        print(f"✅ LLM chose: {chart_config['chart_type']}")
        
        return chart_config
        
    except Exception as e:
        print(f"❌ LLM error: {e}")
        # Fallback
        return {
            "chart_type": "table",
            "title": "Query Results",
            "columns": columns,
            "data": data
        }