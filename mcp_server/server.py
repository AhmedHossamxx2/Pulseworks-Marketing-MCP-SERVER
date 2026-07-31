import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context

# Configure server logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("PulseworksMCPServer")

# ------------------------------------------------------------------------------
# Active Session State (Used for Role Checks and Dynamic Notifications)
# ------------------------------------------------------------------------------
session_state: Dict[str, Any] = {
    "emp_role_in_campaign": "Director",  # Default role: 'Director' or 'Viewer'
    "employee_id": 1,
    "active_campaign_id": 1
}

# ------------------------------------------------------------------------------
# FastMCP Server Initialization & Capability Declarations (Issue #3)
# ------------------------------------------------------------------------------
mcp = FastMCP(
    name="Pulseworks Marketing MCP Server",
    instructions=(
        "You are the Pulseworks Marketing Operations MCP Server. "
        "You manage scoped data access to marketing campaigns, budgets, ad copy, and analytics."
    )
)

BASE_DIR = Path(__file__).resolve().parent


def get_declared_server_capabilities() -> Dict[str, Any]:
    """
    Returns declared server capabilities for protocol negotiation during initialization.
    """
    return {
        "tools": {"listChanged": True},
        "resources": {"subscribe": False, "listChanged": True},
        "prompts": {"listChanged": True},
        "elicitation": {"supported": True},
        "sampling": {"supported": True},
        "logging": {}
    }


def check_client_capability(ctx: Optional[Context], capability_name: str) -> bool:
    """
    Safely inspects whether the connected MCP client declared support for a feature
    (e.g., 'elicitation', 'sampling') during initialization.
    """
    if not ctx:
        logger.warning("No request context available. Defaulting '%s' capability to False.", capability_name)
        return False

    client_caps = getattr(ctx.session, "client_capabilities", {}) if hasattr(ctx, "session") else {}
    has_cap = client_caps.get(capability_name, False)
    logger.info("Capability check for '%s': %s", capability_name, has_cap)
    return bool(has_cap)


# ------------------------------------------------------------------------------
# Register Diagnostic & Fallback Tools
# ------------------------------------------------------------------------------
@mcp.tool(
    name="check_system_capabilities",
    description="Inspects active protocol negotiation capabilities declared by the server and client."
)
async def check_system_capabilities(ctx: Context) -> dict:
    """Diagnostic tool to verify client/server capability exchange."""
    server_caps = get_declared_server_capabilities()
    client_supports_elicitation = check_client_capability(ctx, "elicitation")
    client_supports_sampling = check_client_capability(ctx, "sampling")

    return {
        "status": "Negotiation Active",
        "server_capabilities": server_caps,
        "client_capabilities": {
            "elicitation_supported": client_supports_elicitation,
            "sampling_supported": client_supports_sampling
        },
        "active_session_role": session_state.get("emp_role_in_campaign")
    }


# ------------------------------------------------------------------------------
# Register Resources & Prompts
# ------------------------------------------------------------------------------
@mcp.resource("guidelines://brand_safety")
def get_brand_safety_guidelines() -> str:
    """Exposes read-only Brand Safety Guidelines to the AI Agent."""
    guidelines_path = BASE_DIR / "resources" / "brand_safety_guidelines.md"
    if not guidelines_path.exists():
        return "Brand safety guidelines document is currently unavailable."
    return guidelines_path.read_text(encoding="utf-8")


@mcp.prompt("draft_monthly_client_report")
def draft_monthly_client_report(client_name: str, reporting_month: str) -> str:
    """Returns a structured prompt template for drafting a monthly marketing performance report."""
    return f"""
You are drafting an executive marketing report for **{client_name}** covering **{reporting_month}**.

Please structure the report using the following format:
1. Executive Summary
2. Active Campaigns Performance (Impressions, Clicks, Conversions)
3. Budget Utilization & Spend Analysis
4. Recommendations for Next Month

Ensure all generated ad recommendations adhere to the brand safety guidelines available at `guidelines://brand_safety`.
"""


# ------------------------------------------------------------------------------
# Register Defensive Tools, Progress Tracking, and Sampling
# ------------------------------------------------------------------------------
from mcp_server.tools import register_defensive_tools
register_defensive_tools(mcp)


# ------------------------------------------------------------------------------
# Transport & Entry Point
# ------------------------------------------------------------------------------
def main():
    """Main execution function for uv / pyproject.toml scripts."""
    mcp.run()


if __name__ == "__main__":
    main()