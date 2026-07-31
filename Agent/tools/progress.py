import asyncio
import os
import sys
from typing import Any, Dict, Optional

from langchain_core.tools import tool

# MCP Context for progress tracking
from mcp.server.fastmcp import Context

# ---------------------------------
# Fix imports when running standalone
# ---------------------------------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ======================================================
# 1. MCP-Compliant Heavy Batch Tool
# ======================================================

@tool
async def pull_audience_demographics(
    segment_id: str,
    sample_size: int = 1000,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    DESCRIPTION:
    This tool pulls audience demographic data in batches and provides real-time progress updates.

    WHEN TO USE:
    - Use this tool when the user asks about:
        * progress of data fetching
        * status of a long-running task
        * how much data has been retrieved
        * tracking batch processing
        * audience data retrieval progress
        * loading or fetching audience segments

    DO NOT USE:
    - If the user asks for performance metrics (CTR, CPC, ROAS)
    - If the user asks for campaign analysis or recommendations

    OUTPUT:
    - Returns demographic summary
    - Includes progress updates via MCP (if context is available)
    - Marks operation as long-running

    Pulls audience demographic data in batches with real-time
    MCP progress notifications sent to the client.
    """

    batch_size = 250
    total_fetched = 0

    # -------------------------------
    # Edge Case: Invalid Sample Size
    # -------------------------------
    if sample_size <= 0:
        return {
            "status": "success",
            "segment_id": segment_id,
            "total_records_retrieved": 0,
            "demographic_summary": {},
            "is_long_running": False,
        }

    # -------------------------------
    # Main Batch Processing Loop
    # -------------------------------
    for start in range(0, sample_size, batch_size):
        # Simulate non-blocking long-running operation
        await asyncio.sleep(0.4)

        end = min(start + batch_size, sample_size)
        total_fetched = end

        # ------------------------------------------------------
        # MCP Progress Reporting (Protocol-Level)
        # ------------------------------------------------------
        if getattr(ctx, "report_progress", None):
            try:
                await ctx.report_progress(
                    progress=total_fetched,
                    total=sample_size
                )

                await ctx.info(
                    f"Fetched {total_fetched}/{sample_size} records for segment '{segment_id}'"
                )

            except Exception as e:
                print(f"⚠️ [PROGRESS REPORT ERROR]: {e}")
        else:
            # Local CLI fallback
            pct = (total_fetched / sample_size) * 100
            print(
                f"⏳ [LOCAL PROGRESS {pct:5.1f}%] "
                f"Fetched {total_fetched}/{sample_size}"
            )

    # -------------------------------
    # Ensure Final 100% Progress Event
    # -------------------------------
    if getattr(ctx, "report_progress", None):
        try:
            await ctx.report_progress(
                progress=sample_size,
                total=sample_size
            )
        except Exception as e:
            print(f"⚠️ [FINAL PROGRESS ERROR]: {e}")

    # -------------------------------
    # Final Result
    # -------------------------------
    return {
        "status": "success",
        "segment_id": segment_id,
        "total_records_retrieved": total_fetched,
        "demographic_summary": {
            "primary_age_group": "25-34",
            "top_geography": "North America",
            "top_interests": ["Technology", "Marketing", "SaaS"],
            "engagement_rate": "8.4%",
        },
        "is_long_running": True,
    }


# ======================================================
# Standalone Test Execution
# ======================================================

if __name__ == "__main__":
    async def run_standalone_test():
        print("--- Testing Progress Tracking Tool (Local CLI Mode) ---\n")

        result = await pull_audience_demographics(
            segment_id="SEG-PULSE-ENTERPRISE",
            sample_size=1000,
            ctx=None  # No MCP session → CLI fallback
        )

        print("\n--- Final Output ---")
        print(result)

    asyncio.run(run_standalone_test())