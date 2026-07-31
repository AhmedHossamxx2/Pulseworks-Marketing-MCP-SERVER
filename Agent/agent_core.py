import os
import sys
import traceback
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool

# Ensure root directory is added to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm import create_llm
from mcp_server.tools import (
    pull_audience_demographics,
    analyze_ad_performance_and_recommend,
    request_budget_update
)

# ======================================================
# SYSTEM PROMPT
# ======================================================
SYSTEM_PROMPT = """
You are an expert AI Marketing & Analytics Assistant integrated with MCP tools for Pulseworks Marketing.

Capabilities:
1. Audience Demographics with progress tracking
2. Campaign Performance Analysis and LLM Sampling Recommendations
3. Campaign Budget Updates with multi-layer defensive validation

Rules:
- ALWAYS use tools for fetching real marketing data and modifying state.
- NEVER fabricate metrics or budgets.
- Summarize tool outputs clearly.
- If a tool returns a rejection (e.g., REJECTED_BY_SCHEMA_GUARDRAILS or FORBIDDEN_ROLE), explain the failure reason directly to the user.
- Always rely strictly on tool outputs.
"""

# ======================================================
# TOOL INJECTION (WITH / WITHOUT MCP CONTEXT)
# ======================================================
def get_injected_tools(ctx: Optional[Any] = None) -> List[Any]:
    """
    Returns tools, optionally wrapping them with the active MCP execution context.
    """
    if ctx is None:
        return [
            pull_audience_demographics,
            analyze_ad_performance_and_recommend,
            request_budget_update
        ]

    @tool("pull_audience_demographics")
    async def pull_audience_demographics_mcp(segment_id: str, sample_size: int = 1000):
        """Fetches audience demographic data with progress tracking."""
        return await pull_audience_demographics(segment_id=segment_id, sample_size=sample_size, ctx=ctx)

    @tool("analyze_ad_performance_and_recommend")
    async def analyze_ad_performance_and_recommend_mcp(campaign_id: int):
        """Analyzes campaign performance and invokes sampling for recommendations."""
        return await analyze_ad_performance_and_recommend(campaign_id=campaign_id, ctx=ctx)

    @tool("request_budget_update")
    async def request_budget_update_mcp(campaign_id: int, new_daily_limit: float, currency: str = "USD"):
        """Validates and requests campaign budget updates through defensive guardrails."""
        return await request_budget_update(
            campaign_id=campaign_id,
            new_daily_limit=new_daily_limit,
            currency=currency,
            ctx=ctx
        )

    return [
        pull_audience_demographics_mcp,
        analyze_ad_performance_and_recommend_mcp,
        request_budget_update_mcp
    ]


# ======================================================
# MAIN AGENT EXECUTION LOOP
# ======================================================
async def run_agent_query(
    user_input: str,
    chat_history: Optional[List[BaseMessage]] = None,
    ctx: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Executes a user query through Gemini LLM bound with active MCP tools.
    """
    try:
        llm = create_llm()
        tools = get_injected_tools(ctx)
        llm_with_tools = llm.bind_tools(tools)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if chat_history:
            for m in chat_history:
                messages.append({"role": m.type, "content": m.content})

        messages.append({"role": "user", "content": user_input})
        intermediate_steps = []

        # Tool execution loop (max 5 iterations to prevent infinite loops)
        for _ in range(5):
            response = await llm_with_tools.ainvoke(messages)

            # If model gives final text response without tool calls
            if not getattr(response, "tool_calls", None):
                return {
                    "status": "success",
                    "output": response.content,
                    "intermediate_steps": intermediate_steps,
                }

            tool_map = {getattr(t, "name", getattr(t, "__name__", str(t))): t for t in tools}

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                if tool_name not in tool_map:
                    continue

                tool_func = tool_map[tool_name]

                # Invoke tool
                if hasattr(tool_func, "ainvoke"):
                    tool_result = await tool_func.ainvoke(tool_args)
                else:
                    tool_result = await tool_func(**tool_args) if isinstance(tool_args, dict) else await tool_func(tool_args)

                intermediate_steps.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": tool_result
                })

                # Append assistant tool call message
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [tool_call]
                })

                # Append tool execution result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(tool_result)
                })

        return {
            "status": "error",
            "output": "Agent stopped after reaching maximum tool iterations.",
            "intermediate_steps": intermediate_steps,
        }

    except Exception as e:
        return {
            "status": "error",
            "output": str(e),
            "traceback": traceback.format_exc(),
            "intermediate_steps": [],
        }