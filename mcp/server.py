from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
from athena_tool import run_athena_query

mcp = FastMCP("athena-mcp-server", json_response=True)

@mcp.tool()
def athena_query(sql: str) -> Dict[str, Any]:
    """
    Execute SQL on Athena and return structured results.
    """
    if not sql.lower().strip().startswith("select"):
        raise ValueError("Only SELECT queries allowed")

    return run_athena_query(sql)

if __name__ == "__main__":
    print("MCP Athena Server running at http://127.0.0.1:8000")
    mcp.run(transport="streamable-http")