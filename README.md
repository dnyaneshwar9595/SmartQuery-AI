# SmartQuery-AI

A **multi-agent AI system** that converts natural language questions into SQL queries, executes them on AWS Athena, and renders interactive visualizations — all through a conversational chat interface.

> Ask *"Plot male vs female count as a bar chart"* and the system autonomously generates SQL, fetches data, and renders a Plotly chart.

---

## How It Works

The system uses an **orchestrator-worker architecture** with two layers:

**Outer Layer (LangGraph)** — A state graph that routes requests between specialist agents using LLM tool-calling (no hardcoded rules).

**Inner Layer (ReAct Agents)** — Each worker is a `create_agent` ReAct loop that autonomously picks and calls tools until the task is done.

```
User Message
     │
     ▼
┌─────────────┐      ┌──────────────┐
│ Orchestrator │─────▶│  Data Agent   │  generate_sql → validate_sql → execute_sql
│  (LLM picks  │      └──────┬───────┘
│   next agent) │             │
│              │◀─────────────┘
│              │      ┌──────────────┐
│              │─────▶│  Viz Agent    │  create_chart_config, modify_chart_type
│              │      └──────┬───────┘
│              │◀─────────────┘
│              │      ┌──────────────┐
│              │─────▶│ Analysis Agent│  analyze_data
│              │      └──────┬───────┘
│              │◀─────────────┘
│              │
│              │─────▶ Synthesizer ──▶ END
└─────────────┘
```

- **Orchestrator** — Decides which agent to call next via LLM tool-calling (`tool_choice="required"`).
- **Data Agent** — Generates, validates (LLM-powered), and executes SQL on Athena.
- **Viz Agent** — Creates Plotly chart configs from query results.
- **Analysis Agent** — Provides factual summaries and insights from data.
- **Synthesizer** — Assembles the final response for the user.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestration** | LangGraph | State graph, conditional routing, checkpointing, agent loops |
| **Agents** | LangChain (`create_agent`) | ReAct agent pattern for autonomous tool-calling workers |
| **LLM** | OpenAI GPT-4o-mini | NLU, SQL generation, routing decisions, validation, chart selection |
| **Observability** | LangSmith | Tracing, debugging, and monitoring agent runs end-to-end |
| **Database** | AWS Athena (Presto SQL) | Cloud data warehouse — query source |
| **Persistence** | PostgreSQL | Conversation threads, chat history, LangGraph checkpointer |
| **UI** | Streamlit | Chat interface with thread management sidebar |
| **Visualization** | Plotly | Interactive charts (bar, pie, line, scatter, area, table) |
| **Data** | Pandas | DataFrame manipulation and type handling |
| **AWS SDK** | Boto3 | Athena connection and query execution |
| **Config** | python-dotenv | Environment variable management |

---

## Project Structure

```
SmartQuery-AI/
├── app.py                        # Streamlit entry point
├── config.py                     # Environment & API configuration
├── core/
│   ├── orchestrator_graph.py     # LangGraph state graph + routing + synthesizer
│   ├── agents.py                 # 3 ReAct agent factories (data, viz, analysis)
│   ├── tools.py                  # 6 tools grouped by agent
│   ├── state.py                  # WorkflowState (TypedDict + reducers)
│   └── helpers.py                # LLM singletons, SQL & chart generation
├── database/
│   ├── athena_connection.py      # AWS Athena client
│   ├── athena_utils.py           # LLM-powered SQL validation & execution
│   ├── chat_history.py           # Message & thread persistence
│   ├── checkpointer.py           # PostgreSQL checkpointer for LangGraph
│   ├── connection.py             # DB connection helpers
│   ├── schema_utils.py           # Schema introspection
│   └── threads.py                # Thread CRUD operations
├── prompts/
│   └── templates.py              # Shared prompt templates
├── ui/
│   ├── chat.py                   # Chat interface + workflow invocation
│   ├── sidebar.py                # Thread management sidebar
│   ├── chart_renderer.py         # Plotly chart rendering (7 types)
│   └── utils.py                  # Streaming & conversation loading
└── utils/
    ├── dataframe_helper.py       # DataFrame utilities
    └── session.py                # Streamlit session state management
```

---

## Quick Start

```bash
# Clone & install
git clone <repo-url>
cd SmartQuery-AI
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in: OPENAI_API_KEY, AWS credentials, PostgreSQL URL, LANGSMITH_API_KEY

# Run
streamlit run app.py
```

---

## Key Design Decisions

- **LLM-based routing** over keyword matching — handles rephrasings, is extensible (add a tool = add an agent).
- **LLM-based SQL validation** over regex rules — understands semantic safety, not just pattern matching.
- **Orchestrator loop with workers** — agents can be chained (data → viz) through repeated orchestrator decisions.
- **Checkpointing with PostgreSQL** — full state persistence; survives crashes and enables multi-thread conversations.

---

*Built with LangGraph, LangChain, OpenAI, LangSmith, and AWS Athena*
