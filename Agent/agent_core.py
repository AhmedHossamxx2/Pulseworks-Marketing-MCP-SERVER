import os
import sys
import traceback
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool

# Fix imports when running standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm import create_llm

# Base MCP Tools
from mcp_server.tools import pull_audience_demographics
from mcp_server.tools import analyze_ad_performance_and_recommend


# ======================================================
# 1. SYSTEM PROMPT
# ======================================================

SYSTEM_PROMPT = """
You are an expert AI Marketing & Analytics Assistant integrated with MCP tools.

Capabilities:
1. Audience Demographics
2. Campaign Performance Analysis

Rules:
- ALWAYS use tools for real data.
- NEVER fabricate metrics.
- Summarize tool outputs clearly.
- If tool returns an error, show it to the user.
- Do NOT generate fake campaign data.
- Always rely on tool output.
If the user asks about progress, status, or tracking of data retrieval,
you MUST use the tool pull_audience_demographics.
"""


# ======================================================
# 2. TOOL INJECTION (WITH / WITHOUT MCP CONTEXT)
# ======================================================

def get_injected_tools(ctx: Optional[Any] = None) -> List[Any]:
    """
    Returns tools, optionally wrapped with MCP context.
    """

    if ctx is None:
        return [
            pull_audience_demographics,
            analyze_ad_performance_and_recommend
        ]

    # --- MCP Wrapped Tools ---
    @tool("pull_audience_demographics")
    async def pull_audience_demographics_mcp(segment_id: str, sample_size: int = 1000):
        """Fetches audience demographic data."""
        return await pull_audience_demographics.ainvoke({
            "segment_id": segment_id,
            "sample_size": sample_size,
            "ctx": ctx
        })

    @tool("analyze_ad_performance_and_recommend")
    async def analyze_ad_performance_and_recommend_mcp(campaign_id: str):
        """Analyzes campaign performance and returns recommendations."""
        return await analyze_ad_performance_and_recommend.ainvoke({
            "campaign_id": campaign_id,
            "ctx": ctx
        })

    return [
        pull_audience_demographics_mcp,
        analyze_ad_performance_and_recommend_mcp
    ]


# ======================================================
# 3. MAIN AGENT FUNCTION
# ======================================================

async def run_agent_query(
    user_input: str,
    chat_history: Optional[List[BaseMessage]] = None,
    ctx: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Main agent execution function.
    """

    try:
        llm = create_llm()
        tools = get_injected_tools(ctx)

        # Bind tools to model (modern approach)
        llm_with_tools = llm.bind_tools(tools)

        # Build initial messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if chat_history:
            for m in chat_history:
                messages.append({
                    "role": m.type,
                    "content": m.content
                })

        messages.append({"role": "user", "content": user_input})

        intermediate_steps = []

        # ======================================================
        # 4. TOOL LOOP (CRITICAL)
        # ======================================================

        for _ in range(5):  # prevent infinite loops
            response = await llm_with_tools.ainvoke(messages)

            # لو مفيش tool calls → خلاص
            if not getattr(response, "tool_calls", None):
                final_output = response.content
                return {
                    "status": "success",
                    "output": final_output,
                    "intermediate_steps": intermediate_steps,
                }

            # لو فيه tool calls
            tool_map = {getattr(t, "name", getattr(t, "__name__", str(t))): t for t in tools}

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                if tool_name not in tool_map:
                    continue

                # Execute tool
                tool_func = tool_map[tool_name]

# التحقق مما إذا كانت الأداة تدعم ainvoke أو استدعاؤها كدالة بايثون عادية
                if hasattr(tool_func, "ainvoke"):
                    tool_result = await tool_func.ainvoke(tool_args)
                else:
                    if isinstance(tool_args, dict):
                        tool_result = await tool_func(**tool_args)
                    else:
                        tool_result = await tool_func(tool_args)

                intermediate_steps.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": tool_result
                })

                # Append assistant tool call
                messages.append({
                    "role": "assistant",
                     "content": "",
                    "tool_calls": [tool_call]
                })

                # Append tool result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(tool_result)
                })

        # لو وصلنا هنا → loop خلص بدون رد نهائي
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