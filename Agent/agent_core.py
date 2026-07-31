import os
import sys
import traceback
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

# Fix imports when running standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config
from utils.llm import create_llm

# ======================================================
# 1. SYSTEM PROMPT
# ======================================================

SYSTEM_PROMPT = """
You are an expert AI Marketing & Analytics Assistant integrated with Pulseworks MCP tools.

Capabilities:
1. Audience Demographics (Progress Tracking)
2. Campaign Performance Analysis (Sampling / Recommendations)
3. Budget Updates (Role Authorization)

Rules:
- ALWAYS use tools for real data.
- NEVER fabricate metrics or campaign states.
- Summarize tool outputs clearly.
- If tool returns an error (e.g., unauthorized or rejected), show it to the user.
- Always rely on tool output.
If the user asks about progress, status, or tracking of data retrieval,
you MUST use the tool pull_audience_demographics.
"""

# ======================================================
# 2. MAIN AGENT FUNCTION (MCP PROTOCOL COMPLIANT)
# ======================================================

async def run_agent_query(
    user_input: str,
    chat_history: Optional[List[BaseMessage]] = None,
    ctx: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Main agent execution function.
    Connects to the FastMCP server via standard MCP transport wire.
    """
    try:
        # Determine command args for launching the server process
        server_args = config.MCP_SERVER_COMMAND.split()
        command = server_args[0]
        args = server_args[1:] if len(server_args) > 1 else []

        # ------------------------------------------------------
        # LAYER 1: Establish Real MCP Client Connection
        # ------------------------------------------------------
        async with MultiServerMCPClient({
            "pulseworks_server": {
                "command": command,
                "args": args,
                "transport": config.MCP_TRANSPORT_TYPE
            }
        }) as mcp_client:

            # ------------------------------------------------------
            # LAYER 2: Dynamic Tool Discovery 
            # ------------------------------------------------------
            tools = mcp_client.get_tools()
            llm = create_llm()
            llm_with_tools = llm.bind_tools(tools)

            # Build initial messages
            messages = [SystemMessage(content=SYSTEM_PROMPT)]
            if chat_history:
                messages.extend(chat_history)
            
            messages.append(HumanMessage(content=user_input))
            intermediate_steps = []

            # ------------------------------------------------------
            # LAYER 3: Tool Execution Loop (Max 5 Iterations)
            # ------------------------------------------------------
            for _ in range(5): 
                response = await llm_with_tools.ainvoke(messages)

                # If there are no tool calls, the LLM has its final answer
                if not getattr(response, "tool_calls", None):
                    return {
                        "status": "success",
                        "output": response.content,
                        "intermediate_steps": intermediate_steps,
                    }

                # Add the LLM's tool call request to the message history
                messages.append(response)

                tool_map = {t.name: t for t in tools}

                # Execute requested tools
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    if tool_name not in tool_map:
                        messages.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            content=f"Error: Tool {tool_name} not found on the MCP server."
                        ))
                        continue

                    # Execute tool via MCP Adapter
                    tool_func = tool_map[tool_name]
                    tool_result = await tool_func.ainvoke(tool_args)

                    intermediate_steps.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": tool_result
                    })

                    # Append tool result to context so LLM can read it
                    messages.append(ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=str(tool_result)
                    ))

            # If loop exhausted without final output
            return {
                "status": "error",
                "output": "Agent stopped after max tool iterations.",
                "intermediate_steps": intermediate_steps,
            }

    except Exception as e:
        return {
            "status": "error",
            "output": str(e),
            "traceback": traceback.format_exc(),
            "intermediate_steps": [],
        }