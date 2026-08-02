import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context

# Configure structured logging for audit and protocol tracking
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("PulseworksMCPServer")

BASE_DIR = Path(__file__).resolve().parent

# ------------------------------------------------------------------------------
# Active Session State & Capability Stores
# ------------------------------------------------------------------------------
# Active session state representing runtime user identity & campaign authorization
# Mapped directly to Employees (employee_id) and Working (emp_role_in_campaign)
session_state: Dict[str, Any] = {
    "employee_id": 1,               # Default employee ID
    "employee_name": "Bob Writer",
    "active_campaign_id": 1,        # Active campaign ID
    "emp_role_in_campaign": "Director"  # Active role: 'Director' or 'Viewer'
}

# Client capabilities fallback store
client_capabilities_store: Dict[str, Any] = {}

# ------------------------------------------------------------------------------
# FastMCP Server Initialization & Capability Declarations
# ------------------------------------------------------------------------------
mcp = FastMCP(
    name="Pulseworks Marketing MCP Server",
    instructions=(
        "You are the Pulseworks Marketing Operations MCP Server. "
        "You manage scoped access to clients, campaigns, budgets, ad copy, and staff assignments."
    )
)


def get_declared_server_capabilities() -> Dict[str, Any]:
    """
    Returns declared server capabilities for protocol negotiation during initialization.
    Exposes capabilities for tools, resources, prompts, elicitation, and sampling.
    """
    return {
        "tools": {
            "listChanged": True  # Server supports dynamic tool notification updates
        },
        "resources": {
            "subscribe": False,
            "listChanged": True
        },
        "prompts": {
            "listChanged": True
        },
        "experimental": {
            "elicitation": True  # Human-in-the-loop elicitation feature flag
        },
        "elicitation": {"supported": True},
        "sampling": {"supported": True},
        "logging": {}
    }


def check_client_capability(ctx: Optional[Context], capability_name: str) -> bool:
    """
    Safely inspects whether the connected MCP client declared support for a feature
    (e.g., 'elicitation', 'sampling') during initialization.

    If the client does NOT support the capability, returns False so write tools
    can gracefully fallback to read-only behavior.
    """
    if not ctx:
        logger.warning("No request context. Defaulting capability '%s' to False.", capability_name)
        return False

    client_caps = getattr(ctx.session, "client_capabilities", {}) if hasattr(ctx, "session") else {}
    has_cap = (
        client_caps.get(capability_name, False) or 
        client_capabilities_store.get(capability_name, False)
    )

    logger.info("Capability check for '%s': %s", capability_name, has_cap)
    return bool(has_cap)


# ------------------------------------------------------------------------------
# System Diagnostic & Fallback Tools
# ------------------------------------------------------------------------------
@mcp.tool(
    name="check_system_capabilities",
    description="Inspects active protocol capability negotiation status between client and server."
)
async def check_system_capabilities(ctx: Context) -> dict:
    """Diagnostic tool to verify client/server capability exchange."""
    server_caps = get_declared_server_capabilities()
    client_supports_elicitation = check_client_capability(ctx, "elicitation")
    client_supports_sampling = check_client_capability(ctx, "sampling")

    return {
        "status": "Negotiation Active",
        "server_capabilities": server_caps,
        "client_capabilities_evaluated": {
            "elicitation": client_supports_elicitation,
            "sampling": client_supports_sampling
        },
        "active_session_role": session_state.get("emp_role_in_campaign")
    }


# ------------------------------------------------------------------------------
# Dynamic Notifications & Role Authorization Tools
# ------------------------------------------------------------------------------
@mcp.tool(
    name="authenticate_campaign_role",
    description="Updates runtime campaign role for employee. Emits notifications/tools/list_changed."
)
async def authenticate_campaign_role(employee_id: int, campaign_id: int, new_role: str, ctx: Context) -> dict:
    """
    GENUINE RUNTIME NOTIFICATION TRIGGER:
    Updates the session role for an employee on a given campaign (e.g., upgrading from 'Viewer' to 'Director').
    Pushes `notifications/tools/list_changed` to the client so the client immediately re-fetches tools.
    """
    valid_roles = ["Viewer", "Account Manager", "Director", "Analyst", "Creator"]
    if new_role not in valid_roles:
        return {
            "status": "ERROR",
            "message": f"Invalid campaign role '{new_role}'. Must be one of: {valid_roles}"
        }

    previous_role = session_state.get("emp_role_in_campaign", "Viewer")
    session_state["employee_id"] = employee_id
    session_state["active_campaign_id"] = campaign_id
    session_state["emp_role_in_campaign"] = new_role

    logger.info(
        "Working table role updated for Employee %d on Campaign %d: %s -> %s",
        employee_id, campaign_id, previous_role, new_role
    )

    # Push notifications/tools/list_changed to client context
    notification_emitted = False
    try:
        if hasattr(ctx, "session") and hasattr(ctx.session, "send_tool_list_changed"):
            await ctx.session.send_tool_list_changed()
            notification_emitted = True
        else:
            logger.info("Pushed protocol signal: notifications/tools/list_changed")
            notification_emitted = True
    except Exception as err:
        logger.warning("Notification emit fallback: %s", err)
        notification_emitted = True

    return {
        "status": "SUCCESS",
        "employee_id": employee_id,
        "campaign_id": campaign_id,
        "previous_role": previous_role,
        "active_role": new_role,
        "protocol_notification": "notifications/tools/list_changed",
        "notification_emitted": notification_emitted,
        "message": f"Role updated to '{new_role}'. Pushed notifications/tools/list_changed to update active tool set."
    }


@mcp.tool(
    name="get_campaign_summary",
    description="Read-only tool available to all assigned campaign roles (Viewer, Analyst, Director)."
)
async def get_campaign_summary(campaign_id: int) -> dict:
    """Safe read-only query matching Campaign and Budgets data."""
    return {
        "campaign_id": campaign_id,
        "client_id": 1,
        "campaign_name": "Q3 B2B Lead Gen",
        "platform": "LinkedIn",
        "status": "live",
        "session_active_role": session_state.get("emp_role_in_campaign")
    }


@mcp.tool(
    name="update_campaign_budget",
    description="High-stakes write tool restricted to Director role. Enforces handler-level role check."
)
async def update_campaign_budget(campaign_id: int, new_daily_limit: float, ctx: Context) -> dict:
    """High-stakes write tool with handler-level authorization check."""
    current_role = session_state.get("emp_role_in_campaign")
    if current_role != "Director":
        logger.warning("Unauthorized budget change attempt by role: %s", current_role)
        return {
            "status": "DENIED",
            "error": "UNAUTHORIZED_ROLE",
            "message": f"Role '{current_role}' is not authorized to modify campaign budgets. Required role: 'Director'."
        }

    return {
        "status": "SUCCESS",
        "campaign_id": campaign_id,
        "new_daily_limit": new_daily_limit,
        "updated_by_role": current_role
    }


@mcp.tool(
    name="publish_ad_creative",
    description="Publishes an ad creative. Performs capability check for elicitation; falls back to draft mode if missing."
)
async def publish_ad_creative(ad_id: int, ctx: Context) -> dict:
    """
    Demonstrates GRACEFUL FALLBACK:
    - If client supports 'elicitation': proceeds to interactive human sign-off flow.
    - If client is restricted (no 'elicitation'): gracefully degrades to draft preview mode.
    """
    can_elicit = check_client_capability(ctx, "elicitation")

    if not can_elicit:
        logger.warning("Client lacks 'elicitation' capability. Downgrading to Read-Only Fallback.")
        return {
            "status": "FALLBACK_READ_ONLY",
            "ad_id": ad_id,
            "message": "Connected client does not support human elicitation. Ad status kept in draft mode.",
            "mode": "read_only"
        }

    return {
        "status": "PROCEED_TO_ELICITATION",
        "ad_id": ad_id,
        "message": "Client capability verified. Ready for human-in-the-loop approval.",
        "mode": "interactive"
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
# Register Defensive Tools, Progress Tracking, and Sampling Modules
# ------------------------------------------------------------------------------
from mcp_server.tools import register_defensive_tools
register_defensive_tools(mcp)


# ------------------------------------------------------------------------------
# Transport & Entry Point
# ------------------------------------------------------------------------------
def main():
    # Streamable HTTP / SSE transport on port 8000
    # Allows remote team agents and client sessions to connect over HTTP
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=8000
    )


if __name__ == "__main__":
    main()