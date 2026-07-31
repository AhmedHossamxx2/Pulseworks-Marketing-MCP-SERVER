import asyncio
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP, Context  # ✅ Added Context import

# Import your agent
from agent_core import run_agent_query

# ======================================================
# 1. Initialize MCP Server
# ======================================================

mcp = FastMCP("AI Marketing Agent")

# ======================================================
# 2. Main Agent Tool (ENTRY POINT)
# ======================================================

@mcp.tool()
async def marketing_agent(
    query: str,
    ctx: Context  # ✅ CRITICAL: Must be typed as Context for FastMCP to inject it
) -> str:  # ✅ Return a string for cleaner integration with Claude/Clients
    """
    Main entry point for the AI Marketing Agent. 
    Pass your marketing analysis or data retrieval requests here.

    Args:
        query: User query for marketing analysis or data retrieval.
    """
    try:
        # ✅ Notify the client that the agent is starting to think
        await ctx.info(f"Starting analysis for query: '{query}'")

        result = await run_agent_query(
            user_input=query,
            chat_history=[],   # MCP usually stateless per call
            ctx=ctx            # Passes MCP context to LangChain tools
        )

        if result["status"] == "success":
            return result["output"]
        else:
            return f"Agent encountered an issue: {result['output']}"

    except Exception as e:
        return f"Server error: {str(e)}"

# ======================================================
# 3. Health Check Tool
# ======================================================

@mcp.tool()
async def health_check() -> str:
    """
    Simple health check endpoint.
    """
    return "✅ MCP server is running and healthy."

# ======================================================
# 4. Run Server (STDIO TRANSPORT)
# ======================================================

if __name__ == "__main__":
    print("🚀 Starting MCP Server (stdio transport)...")
    # stdio is standard for Claude Desktop / Cursor integrations
    mcp.run(transport="stdio")