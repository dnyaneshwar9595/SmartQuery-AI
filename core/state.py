from typing import TypedDict, Annotated, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class QueryResults(TypedDict):
    """Serializable query results"""
    columns: List[str]
    data: List[List[Any]]
    dtypes: Optional[Dict[str, str]]

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    query_results: Optional[QueryResults]  # Serializable query results
    chart_config: Optional[Dict[str, Any]]  # Chart configuration for UI