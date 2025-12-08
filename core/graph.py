from langgraph.graph import StateGraph, START, END
from core.state import ChatState
from core.nodes import (
    athena_query_node,
    chart_config_node,
    general_chat_node
)
from database.checkpointer import get_checkpointer

# Global workflow instance
_workflow = None

def route_after_classification(state: ChatState) -> str:
    """
    Route to database pipeline or general chat based on classification
    """
    messages = state['messages']
    last_message = messages[-1].content
    
    keywords = ['select', 'fetch']
    if any(keyword in last_message.lower() for keyword in keywords):
        return "athena_query"
    else:
        state['chart_config'] = None
        state['query_results'] = None
        return "general_chat"

def create_workflow():
    """Create and compile the LangGraph workflow with conditional routing"""
    
    # Build graph
    graph = StateGraph(ChatState)
    
    # Add all nodes
    graph.add_node("athena_query", athena_query_node)
    graph.add_node("chart_config", chart_config_node)
    graph.add_node("general_chat", general_chat_node)
    
    # Add edges    
    # Conditional routing after classification
    graph.add_conditional_edges(
        START,
        route_after_classification,
        {
            "athena_query": "athena_query",
            "general_chat": "general_chat"
        }
    )
    graph.add_edge("athena_query", "chart_config")
    graph.add_edge("athena_query", END)
    graph.add_edge("general_chat", END)
    # Compile with checkpointer
    checkpointer = get_checkpointer()
    workflow = graph.compile(checkpointer=checkpointer)
    
    return workflow

def get_workflow():
    """Get workflow instance (singleton pattern)"""
    global _workflow
    if _workflow is None:
        _workflow = create_workflow()
    return _workflow

# Create workflow instance
workflow = get_workflow()