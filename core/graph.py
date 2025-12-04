from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from core.state import ChatState
from core.nodes import create_chat_node
from tools.search import get_search_tool
from database.checkpointer import get_checkpointer

# Global workflow instance
_workflow = None

def create_workflow():
    """Create and compile the LangGraph workflow"""
    
    # Get tools
    search_tool = get_search_tool()
    tools = [search_tool]
    
    # Create nodes
    chat_node = create_chat_node(tools)
    tool_node = ToolNode(tools)
    
    # Build graph
    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)
    
    # Add edges
    graph.add_edge(START, "chat_node")
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")
    
    workflow = graph.compile()
    
    return workflow

def get_workflow():
    """Get workflow instance (singleton pattern)"""
    global _workflow
    if _workflow is None:
        _workflow = create_workflow()
    return _workflow

# Create workflow instance
workflow = get_workflow()