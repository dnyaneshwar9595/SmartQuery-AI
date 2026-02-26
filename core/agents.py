"""
agents.py — Three specialist ReAct agents built with create_agent.
─────────────────────────────────────────────────────────────────────
Each factory function returns a compiled LangGraph that:
  1. Receives a HumanMessage
  2. Runs the ReAct loop  (Think → Call Tool → Observe → repeat)
  3. Returns a final AIMessage

These compiled agents are invoked INSIDE the outer LangGraph nodes
(see orchestrator_graph.py).
"""

from langchain.agents import create_agent          # builds a ReAct agent graph
from langchain_openai import ChatOpenAI
from config import Config
from core.tools import DATA_AGENT_TOOLS, VIZ_AGENT_TOOLS, ANALYSIS_AGENT_TOOLS


# ── Shared helper: create an LLM with a given temperature ──

def _make_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=Config.MODEL_NAME,
        api_key=Config.OPENAI_API_KEY,
        temperature=temperature,
    )


# ──────────────────────────────────────────────────────────
#  1. DATA AGENT  —  fetches data from Athena
#     Tools: generate_sql → validate_sql → execute_sql
# ──────────────────────────────────────────────────────────

DATA_AGENT_PROMPT = """\
You are a Data Retrieval Agent for AWS Athena.

Steps (follow IN ORDER):
1. generate_sql  — turn the user's question into PRECISE SQL.
2. validate_sql  — check safety.  If INVALID, retry generate_sql (max 2 retries).
3. execute_sql   — run the valid SQL.
4. Return the raw JSON from execute_sql as your FINAL answer.

SQL Precision Rules:
- When the user mentions specific categories (e.g. "male vs female",
  "survived vs deceased"), add a WHERE clause to filter ONLY those values.
  Example: WHERE gender IN ('Male', 'Female')
- Always exclude NULL values unless the user explicitly asks about them.
  Example: WHERE column IS NOT NULL
- Use LOWER() or TRIM() for string matching when data may be inconsistent.
- The goal is to return EXACTLY the data the user asked for — nothing more.

General Rules:
- Do NOT summarise or reformat the data.
- If all retries fail, explain the error."""


def create_data_agent():
    return create_agent(
        model=_make_llm(0.3),
        tools=DATA_AGENT_TOOLS,
        system_prompt=DATA_AGENT_PROMPT,
        name="data_agent",
    )


# ──────────────────────────────────────────────────────────
#  2. VISUALIZATION AGENT  —  creates / modifies charts
#     Tools: create_chart_config, modify_chart_type
# ──────────────────────────────────────────────────────────

VIZ_AGENT_PROMPT = """\
You are a Visualization Agent.

Chart types: pie, bar, bar_horizontal, line, scatter, area, table.

Actions:
- Given query results → call create_chart_config.
- Asked to change chart type → call modify_chart_type.

Your final message MUST include the chart config JSON inside tags:
<CHART_CONFIG>{ ... }</CHART_CONFIG>"""


def create_viz_agent():
    return create_agent(
        model=_make_llm(0),
        tools=VIZ_AGENT_TOOLS,
        system_prompt=VIZ_AGENT_PROMPT,
        name="viz_agent",
    )


# ──────────────────────────────────────────────────────────
#  3. ANALYSIS AGENT  —  interprets data
#     Tools: analyze_data
# ──────────────────────────────────────────────────────────

ANALYSIS_AGENT_PROMPT = """\
You are a Data Analysis Agent.

- Call analyze_data, then give a clear, factual summary.
- Only state what is explicitly in the data — no hallucination.
- If no data exists, ask the user to query data first."""


def create_analysis_agent():
    return create_agent(
        model=_make_llm(0.5),
        tools=ANALYSIS_AGENT_TOOLS,
        system_prompt=ANALYSIS_AGENT_PROMPT,
        name="analysis_agent",
    )
