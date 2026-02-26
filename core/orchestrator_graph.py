"""
orchestrator_graph.py — The main workflow (read top-to-bottom).
═══════════════════════════════════════════════════════════════

HOW IT WORKS
─────────────
This file wires everything together using two layers:

  OUTER LAYER  (LangGraph StateGraph)
    Provides: nodes, edges, conditional routing, loops, checkpointing.
    You can visualise it as:

        START ──→ orchestrator ──→ data_agent ───→ orchestrator  ↺
                       │         → viz_agent ────→ orchestrator  ↺
                       │         → analysis_agent → orchestrator ↺
                       └────────→ synthesizer ──→ END

  INNER LAYER  (create_agent ReAct workers)
    Each worker node wraps a `create_agent` compiled graph.
    Inside a worker the LLM autonomously calls tools in a loop:
        Think → Pick a tool → Call it → Read result → Think again → …

Reading order:
  1. Routing tools  (how the orchestrator picks a worker)
  2. orchestrator_node  (the "brain")
  3. Worker nodes  (data / viz / analysis)
  4. synthesizer   (builds the final response)
  5. create_workflow  (assembles the graph)
"""

# ── stdlib ──
import json, re, logging

# ── LangGraph / LangChain ──
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool as make_tool
from langchain_openai import ChatOpenAI

# ── Our modules ──
from core.state import WorkflowState
from core.agents import create_data_agent, create_viz_agent, create_analysis_agent
from core.helpers import get_chatbot
from database.checkpointer import get_checkpointer
from config import Config

logger = logging.getLogger(__name__)


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  STEP 1 — ROUTING TOOLS                                         ║
# ║  The orchestrator LLM is forced to call exactly ONE of these.    ║
# ║  The tool it picks = the next node the graph will visit.         ║
# ╚═══════════════════════════════════════════════════════════════════╝

@make_tool
def route_to_data_agent(reason: str) -> str:
    """Pick this when the user needs NEW data from the database.
    Examples: queries, counts, totals, filters, charts that need fresh data.
    ALWAYS pick this if has_data=False and user asks about database content."""
    return "data_agent"

@make_tool
def route_to_viz_agent(reason: str) -> str:
    """Pick this ONLY when data already exists (has_data=True) and the user 
    wants a chart, plot, or wants to change the current chart type."""
    return "viz_agent"

@make_tool
def route_to_analysis_agent(reason: str) -> str:
    """Pick this ONLY when data already exists (has_data=True) and the user 
    asks follow-up analytical questions (trends, averages, comparisons, insights).
    If has_data=False, route to data_agent instead."""
    return "analysis_agent"

@make_tool
def route_to_synthesizer(reason: str) -> str:
    """Pick this when all work is done, or for greetings / general chat."""
    return "synthesizer"


ROUTING_TOOLS = [
    route_to_data_agent,
    route_to_viz_agent,
    route_to_analysis_agent,
    route_to_synthesizer,
]

# Quick lookup: tool function name → graph node name
_TOOL_TO_NODE = {t.name: t.invoke("") for t in ROUTING_TOOLS}
#  e.g. {"route_to_data_agent": "data_agent", ...}


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  STEP 2 — ORCHESTRATOR NODE  (the "brain")                      ║
# ║  Reads the state, asks the LLM to call a routing tool,          ║
# ║  writes the decision into state["next_step"].                    ║
# ╚═══════════════════════════════════════════════════════════════════╝

ORCHESTRATOR_PROMPT = """\
You are the Master Orchestrator.  Look at the user's message and the
current state, then call exactly ONE routing tool to decide the next step.

CRITICAL RULES:
- If has_data=False → ONLY use route_to_data_agent or route_to_synthesizer
- If user asks about database content (counts, queries, totals) and has_data=False 
  → route_to_data_agent
- If user asks for a chart/plot about something DIFFERENT from the current data
  → route_to_data_agent (need fresh data first!)
- Only use route_to_viz_agent when data already exists AND matches what user wants
- Only use route_to_analysis_agent when has_data=True

The tool descriptions tell you when each one is appropriate."""


def orchestrator_node(state: WorkflowState) -> WorkflowState:

    # 1. Read current state
    last_msg      = state["messages"][-1].content if state["messages"] else ""
    has_data      = state.get("query_results") is not None
    has_chart     = state.get("chart_config")  is not None
    worker_output = state.get("worker_output")  # set by workers when they have a final answer

    # 🚨 LOOP PREVENTION: If a worker just ran and left output, go to synthesizer
    if worker_output:
        print("🧠 Orchestrator → synthesizer  (worker left output, finishing)")
        return {"next_step": "synthesizer"}

    # 2. Build a short context string so the LLM knows what's available
    context = f"\nState: has_data={has_data}, has_chart={has_chart}"
    if has_data:
        cols = state["query_results"].get("columns", [])
        rows = len(state["query_results"].get("data", []))
        context += f", columns={cols}, rows={rows}"

    # 3. Ask the LLM — it MUST call one routing tool (tool_choice="required")
    llm = ChatOpenAI(model=Config.MODEL_NAME, api_key=Config.OPENAI_API_KEY, temperature=0)
    llm_with_tools = llm.bind_tools(ROUTING_TOOLS, tool_choice="required")

    response = llm_with_tools.invoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT + context),
        HumanMessage(content=last_msg),
    ])

    # 4. Read the tool call → that's our routing decision
    if response.tool_calls:
        tool_name = response.tool_calls[0]["name"]
        decision  = _TOOL_TO_NODE.get(tool_name, "synthesizer")
        reason    = response.tool_calls[0].get("args", {}).get("reason", "")
    else:
        decision, reason = "synthesizer", "no tool call"

    print(f"🧠 Orchestrator → {decision}  (reason: {reason[:80]})")
    return {"next_step": decision}


def _route_from_state(state: WorkflowState) -> str:
    """Conditional-edge function: just reads what the orchestrator wrote."""
    return state.get("next_step", "synthesizer")


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  STEP 3 — WORKER NODES                                            ║
# ║  Each wraps a create_agent ReAct graph.                           ║
# ║  They run autonomously, then we extract results into outer state. ║
# ╚═══════════════════════════════════════════════════════════════════╝

# Lazy singletons — agents are heavy, create once.
_agents = {"data": None, "viz": None, "analysis": None}

def _agent(name):
    """Get (or create) a cached agent by name."""
    if _agents[name] is None:
        _agents[name] = {
            "data":     create_data_agent,
            "viz":      create_viz_agent,
            "analysis": create_analysis_agent,
        }[name]()
    return _agents[name]


# ── 3a. Data Agent Node ──────────────────────────────────

def data_agent_node(state: WorkflowState) -> WorkflowState:
    """Invoke the Data Agent → extract query results into state."""

    user_msg = state["messages"][-1].content
    print(f"📊 Data Agent starting: {user_msg[:80]}...")

    # Run the ReAct agent (it calls generate_sql → validate → execute internally)
    result   = _agent("data").invoke({"messages": [HumanMessage(content=user_msg)]})
    final    = result["messages"][-1].content if result.get("messages") else ""

    # Try to pull out the JSON with columns + data
    query_results = _extract_json(final, required_keys=["columns", "data"])

    if query_results:
        print(f"✅ Data Agent: {len(query_results.get('data',[]))} rows")
        # NOTE: Do NOT set worker_output here.
        # Leaving it empty lets the orchestrator make a fresh routing decision
        # (e.g. → viz_agent if user asked for a chart, or → synthesizer for text).
        return {"query_results": query_results, "chart_config": None}

    print("⚠️ Data Agent: no valid results extracted")
    return {"worker_output": final}


# ── 3b. Viz Agent Node ───────────────────────────────────

def viz_agent_node(state: WorkflowState) -> WorkflowState:
    """Invoke the Viz Agent → extract chart config into state."""

    user_msg      = state["messages"][-1].content
    query_results = state.get("query_results")
    chart_config  = state.get("chart_config")

    print("📈 Viz Agent starting...")

    # Give the agent the data it needs
    if query_results:
        prompt = f"User asked: {user_msg}\n\nQuery results:\n{json.dumps(query_results, default=str)}"
    elif chart_config:
        prompt = f"User asked: {user_msg}\n\nCurrent chart:\n{json.dumps(chart_config, default=str)}\nModify as requested."
    else:
        prompt = f"User asked: {user_msg}\nNo data available — tell user to query data first."

    result = _agent("viz").invoke({"messages": [HumanMessage(content=prompt)]})
    final  = result["messages"][-1].content if result.get("messages") else ""

    new_chart = _extract_chart_config(final)
    if new_chart:
        print(f"✅ Viz Agent: {new_chart.get('chart_type','chart')} chart created")
        return {"chart_config": new_chart, "worker_output": final}

    print("⚠️ Viz Agent: no chart config extracted")
    return {"worker_output": final}


# ── 3c. Analysis Agent Node ──────────────────────────────

def analysis_agent_node(state: WorkflowState) -> WorkflowState:
    """Invoke the Analysis Agent → store text summary in state."""

    user_msg      = state["messages"][-1].content
    query_results = state.get("query_results")

    print("🔬 Analysis Agent starting...")

    if query_results:
        prompt = f"User asked: {user_msg}\n\nData:\n{json.dumps(query_results, default=str)}"
    else:
        prompt = f"User asked: {user_msg}\n\nNo data available."

    result = _agent("analysis").invoke({"messages": [HumanMessage(content=prompt)]})
    final  = result["messages"][-1].content if result.get("messages") else "No analysis."

    print("✅ Analysis Agent: done")
    return {"worker_output": final, "chart_config": None}


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  STEP 4 — SYNTHESIZER  (final node → END)                       ║
# ║  Reads worker_output / chart_config, writes one AIMessage.       ║
# ╚═══════════════════════════════════════════════════════════════════╝

def synthesizer_node(state: WorkflowState) -> WorkflowState:

    chart   = state.get("chart_config")
    worker  = state.get("worker_output")
    results = state.get("query_results")
    print(f"🎨 Synthesizer: chart={bool(chart)}, worker={bool(worker)}, results={bool(results)}")

    if chart:
        # A chart was created — describe it
        content = f"Here's your **{chart.get('chart_type','chart')}** chart: **{chart.get('title','Data')}**"
        if results:
            content += f"\n\n_Showing {len(results.get('data',[]))} rows of data._"

    elif worker:
        # An agent left a text answer (analysis, error, etc.)
        content = worker

    elif results:
        # Data exists but no chart / no worker text → summarise the data nicely
        llm = get_chatbot()
        resp = llm.invoke([
            SystemMessage(content="You are a helpful data assistant. Present the query results clearly and concisely in a readable format. Use markdown tables or bullet points."),
            HumanMessage(content=f"User asked: {state['messages'][-1].content}\n\nQuery results:\n{json.dumps(results, default=str)}"),
        ])
        content = resp.content

    else:
        # Nothing to show — just chat
        llm = get_chatbot()
        resp = llm.invoke([
            SystemMessage(content="You are a helpful data assistant. Answer conversationally."),
            *state["messages"],
        ])
        content = resp.content

    print(f"💬 Synthesizer: {len(content)} chars")

    return {
        "messages":      [AIMessage(content=content)],
        "worker_output": None,   # clear scratch
        "next_step":     None,   # clear routing
    }


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  STEP 5 — GRAPH ASSEMBLY                                        ║
# ║  Wire the nodes + edges, attach checkpointer, compile.           ║
# ╚═══════════════════════════════════════════════════════════════════╝

def create_workflow():
    """
    Builds:
        START → orchestrator ─┬→ data_agent ─────→ orchestrator  (loop)
                              ├→ viz_agent ──────→ orchestrator  (loop)
                              ├→ analysis_agent ─→ orchestrator  (loop)
                              └→ synthesizer ───→ END
    """
    g = StateGraph(WorkflowState)

    # Register nodes
    g.add_node("orchestrator",    orchestrator_node)
    g.add_node("data_agent",      data_agent_node)
    g.add_node("viz_agent",       viz_agent_node)
    g.add_node("analysis_agent",  analysis_agent_node)
    g.add_node("synthesizer",     synthesizer_node)

    # Entry point
    g.add_edge(START, "orchestrator")

    # Orchestrator → worker (LLM picks which one via tool call)
    g.add_conditional_edges(
        "orchestrator", 
        _route_from_state, 
        {
        "data_agent":     "data_agent",
        "viz_agent":      "viz_agent",
        "analysis_agent": "analysis_agent",
        "synthesizer":    "synthesizer",
    })

    # Every worker loops back to orchestrator (it may send to another worker or finish)
    g.add_edge("data_agent",     "orchestrator")
    g.add_edge("viz_agent",      "orchestrator")
    g.add_edge("analysis_agent", "orchestrator")

    # Synthesizer is the exit
    g.add_edge("synthesizer", END)

    # Compile with PostgreSQL checkpointer (state saved after every node)
    return g.compile(checkpointer=get_checkpointer())


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  HELPERS — parse JSON from agent text responses                  ║
# ╚═══════════════════════════════════════════════════════════════════╝

def _extract_json(text: str, required_keys: list[str]) -> dict | None:
    """Find the first JSON object in `text` that contains all `required_keys`."""
    for m in re.finditer(r'\{.*\}', text, re.DOTALL):
        try:
            obj = json.loads(m.group())
            if all(k in obj for k in required_keys):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _extract_chart_config(text: str) -> dict | None:
    """Pull chart config from <CHART_CONFIG> tags or any JSON with 'chart_type'."""
    # Try tagged format first
    m = re.search(r"<CHART_CONFIG>(.*?)</CHART_CONFIG>", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Fall back to raw JSON
    return _extract_json(text, required_keys=["chart_type"])


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  SINGLETON — compiled once on import                             ║
# ╚═══════════════════════════════════════════════════════════════════╝

workflow = create_workflow()
