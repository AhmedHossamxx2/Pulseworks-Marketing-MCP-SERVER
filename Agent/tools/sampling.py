import os
import sys
from typing import Any, Dict

from langchain_core.tools import tool

# MCP Context + Types
from mcp.server.fastmcp import Context
from mcp.types import SamplingMessage, TextContent

# ---------------------------------
# Fix imports when running standalone
# ---------------------------------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ======================================================
# 1. Mock Data Layer
# ======================================================

def mock_fetch_campaign_metrics(campaign_id: str) -> Dict[str, Any]:
    """Simulates fetching raw performance metrics for a specific ad campaign."""
    return {
        "campaign_id": campaign_id,
        "impressions": 150000,
        "clicks": 3200,
        "ctr_percent": 2.13,
        "conversions": 85,
        "conversion_rate_percent": 2.65,
        "total_spend_usd": 4500.0,
        "cpc_usd": 1.41,
        "cpa_usd": 52.94,
        "roas": 1.85,
    }


# ======================================================
# 2. MCP Sampling-Compliant Tool
# ======================================================

@tool
async def analyze_ad_performance_and_recommend(
    campaign_id: str,
    ctx: Context = None
) -> dict:
    """
    Fetches campaign metrics and evaluates performance.
    """

    print(f"🔥 TOOL CALLED with campaign_id={campaign_id}")

    # ✅ Validation
    VALID_CAMPAIGNS = ["CMP-2026-PULSE", "CMP-2026-ALPHA"]

    if campaign_id not in VALID_CAMPAIGNS:
        return {
            "error": f"Campaign '{campaign_id}' not found.",
            "status": "failed"
        }

    # ✅ Mock data (بس للكامبينات الصح)
    data = {
        "impressions": 150000,
        "clicks": 3200,
        "conversions": 85,
        "spend": 4500
    }

    # حساباتك...
    # -------------------------------
    # Step 1: Fetch Metrics
    # -------------------------------
    metrics = mock_fetch_campaign_metrics(campaign_id)

    # -------------------------------
    # Step 2: Prepare Prompts
    # -------------------------------
    system_prompt = (
        "You are a performance marketing analyst evaluating campaign health "
        "against brand guidelines. Return EXACTLY 1 issue and 1 recommendation. "
        "Maximum 2 sentences total. Be direct and actionable."
    )

    user_prompt = f"""
Analyze these campaign metrics:

Campaign ID: {metrics['campaign_id']}
CTR: {metrics['ctr_percent']}%
Conversion Rate: {metrics['conversion_rate_percent']}%
CPA: ${metrics['cpa_usd']}
ROAS: {raw_metrics_roas if (raw_metrics_roas := metrics.get('roas')) else metrics['roas']}x

Format strictly:
Issue: <text>
Recommendation: <text>
"""

    # -------------------------------
    # Step 3: MCP Sampling Call
    # -------------------------------
    reasoning = ""
    sampling_triggered = False
    fallback_used = False

    if ctx and hasattr(ctx, "session") and ctx.session:
        try:
            sampling_triggered = True

            sampling_response = await ctx.session.create_message(
                messages=[
                    SamplingMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=user_prompt
                        )
                    )
                ],
                system_prompt=system_prompt,
                max_tokens=150,
            )

            # Safe extraction based on MCP client response structure
            if sampling_response and hasattr(sampling_response, "content"):
                content = sampling_response.content
                if hasattr(content, "text"):
                    reasoning = content.text.strip()
                elif isinstance(content, list) and len(content) > 0:
                    reasoning = getattr(content[0], "text", "").strip()

        except Exception as e:
            print(f"⚠️ [MCP SAMPLING ERROR]: {e}")
            fallback_used = True
    else:
        fallback_used = True

    # -------------------------------
    # Step 4: Fallback Logic
    # -------------------------------
    if not reasoning:
        fallback_used = True
        reasoning = (
            "Issue: ROAS is below target due to high CPA. "
            "Recommendation: Reallocate budget to high-converting segments "
            "and pause low-performing creatives."
        )

    # -------------------------------
    # Step 5: Final Response
    # -------------------------------
    return {
        "status": "success",
        "campaign_id": campaign_id,
        "raw_metrics": metrics,
        "ai_sampling_recommendation": reasoning,
        "sampling_triggered": sampling_triggered,
        "mcp_sampling_used": not fallback_used,
        "fallback_used": fallback_used,
    }


# ======================================================
# Standalone Test (Optional)
# ======================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        result = await analyze_ad_performance_and_recommend.invoke(
            {
                "campaign_id": "CMP-2026-PULSE",
                "ctx": None  # No MCP session -> forces fallback locally
            }
        )
        print("\n--- STANDALONE TEST OUTPUT ---")
        print(result)

    asyncio.run(test())