"""
state.py — Shared state that flows through every node in the graph.
─────────────────────────────────────────────────────────────────────
Think of this as a "shared notebook" that every node can read & write.
The PostgreSQL checkpointer saves a snapshot after every node runs.
"""

from typing import TypedDict, Annotated, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# ── Shape of data returned from Athena queries ──
class QueryResults(TypedDict):
    columns: List[str]           # e.g. ["product_name", "price"]
    data:    List[List[Any]]     # e.g. [["Widget", 9.99], ["Gadget", 19.99]]
    dtypes:  Optional[Dict[str, str]]  # e.g. {"price": "double"}


# ── The single state object shared by ALL nodes ──
class WorkflowState(TypedDict):

    # Chat messages (auto-appended via add_messages reducer)
    messages:      Annotated[list[BaseMessage], add_messages]
    thread_id:     Optional[str]

    # Orchestrator writes here; the router reads it to pick the next node
    next_step:     Optional[str]

    # Filled by the Data Agent after querying Athena
    query_results: Optional[QueryResults]

    # Filled by the Viz Agent (Plotly chart spec)
    chart_config:  Optional[Dict[str, Any]]

    # Scratch pad — any worker can leave text here for the synthesizer
    worker_output: Optional[str]
