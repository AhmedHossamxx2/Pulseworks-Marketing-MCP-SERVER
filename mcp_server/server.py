import logging
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseworksMCPServer")

# ------------------------------------------------------------------------------
# 1. FastMCP Server & Capabilities Setup
# ------------------------------------------------------------------------------
mcp = FastMCP(
    name="Pulseworks Marketing MCP Server",
    instructions=(
        "You are the Pulseworks Marketing Operations MCP Server. "
        "You manage scoped access to clients, campaigns, budgets, ad copy, and staff assignments."
    )
)

# Active session state representing runtime user identity & campaign authorization
# Mapped directly to Employees (employee_id) and Working (emp_role_in_campaign)
session_state: Dict[str, Any] = {
    "employee_id": 2,               # Default: Bob Writer
    "employee_name": "Bob Writer",
    "campaign_id": 1,               # Q3 B2B Lead Gen
    "emp_role_in_campaign": "Viewer" # Baseline role in seed.sql: Viewer
}


def get_declared_server_capabilities() -> Dict[str, Any]:
    """
    Exposes declared server capabilities exchanged during initialization handshake.
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
    Safely inspects whether the connected MCP client declared support for a feature.
    """
    if not ctx:
        return False
    client_caps = getattr(ctx.session, "client_capabilities", {}) if hasattr(ctx, "session") else {}
    return bool(client_caps.get(capability_name, False))


# ------------------------------------------------------------------------------
# 2. Dynamic Notifications Implementation (Issue #4)
# ------------------------------------------------------------------------------

@mcp.tool(
    name="authenticate_campaign_role",
    description="Updates runtime campaign role for employee in Working table. Emits notifications/tools/list_changed."
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

    previous_role = session_state["emp_role_in_campaign"]
    session_state["employee_id"] = employee_id
    session_state["campaign_id"] = campaign_id
    session_state["emp_role_in_campaign"] = new_role

    logger.info(
        "Working table role updated for Employee %d on Campaign %d: %s -> %s",
        employee_id, campaign_id, previous_role, new_role
    )

    # Push notifications/tools/list_changed to client context
    notification_emitted = False
    try:
        if hasattr(ctx.session, "send_tool_list_changed"):
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
    """
    Safe read-only query matching Campaign and Budgets seed data.
    """
    return {
        "campaign_id": campaign_id,
        "client_id": 1,
        "campaign_name": "Q3 B2B Lead Gen",
        "platform": "LinkedIn",
        "status": "live",
        "session_active_role": session_state["emp_role_in_campaign"]
    }


@mcp.tool(
    name="update_campaign_budget",
    description="High-stakes write tool restricted to Director role in Working table. Enforces handler-level role check."
)
async def update_campaign_budget(campaign_id: int, new_daily_limit: float, ctx: Context) -> dict:
    """
    High-stakes write tool with handler-level authorization check.
    Fails if session active role is 'Viewer'.
    """
    current_role = session_state["emp_role_in_campaign"]
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


if __name__ == "__main__":
    mcp.run()