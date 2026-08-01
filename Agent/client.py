import asyncio
import logging
import os
import sys
from typing import Optional

from mcp import ClientSession
from mcp.client.sse import sse_client

# Ensure root directory is added to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Agent.agent_core import run_agent_query
from Agent.utils.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseworksMCPClient")


async def progress_handler(progress: float, total: Optional[float]):
    """
    Progress callback listener for long-running MCP tools (Issue #8).
    Prints real-time progress updates when the server reports progress.
    """
    total_val = total if total else 100
    percentage = (progress / total_val) * 100
    logger.info("⏳ [MCP PROGRESS]: Step %.0f/%.0f (%.1f%% complete)", progress, total_val, percentage)


async def run_mcp_sse_client(user_query: str):
    """
    Establishes a real MCP session over Streamable HTTP / SSE (Issue #9),
    performs capability negotiation, and executes the agent query.
    """
    sse_url = getattr(config, "MCP_SERVER_HTTP_URL", "http://localhost:8000/sse")
    
    logger.info("Connecting to Pulseworks MCP Server via SSE at %s...", sse_url)

    try:
        # 1. Open SSE Transport Stream
        async with sse_client(sse_url) as (read, write):
            # 2. Initialize MCP Client Session over SSE
            async with ClientSession(read, write) as session:
                
                # 3. Perform Protocol Handshake
                logger.info("Initiating MCP Handshake over HTTP/SSE...")
                init_result = await session.initialize()
                logger.info("✅ Connected to MCP Server: %s", init_result.serverInfo.name)
                logger.info("Server Capabilities: %s", init_result.capabilities)

                # 4. Discover Available Tools dynamically over SSE
                tools_response = await session.list_tools()
                discovered_tools = [t.name for t in tools_response.tools]
                logger.info("Discovered %d tools over SSE: %s", len(discovered_tools), discovered_tools)

                # 5. Run the Agent query passing the active MCP Session as context
                logger.info("Running Agent Query: '%s'", user_query)
                agent_result = await run_agent_query(
                    user_input=user_query,
                    chat_history=None,
                    ctx=session  # Passes real active MCP SSE session context to tools
                )

                logger.info("Agent Output:\n%s", agent_result.get("output"))
                return agent_result

    except Exception as err:
        logger.error("❌ Failed to connect or execute over SSE transport: %s", err)
        return {"status": "error", "output": str(err)}


if __name__ == "__main__":
    # Test query against active SSE server
    test_query = "Pull audience demographics for segment 'segment_alpha' with sample size 1000"
    asyncio.run(run_mcp_sse_client(test_query))