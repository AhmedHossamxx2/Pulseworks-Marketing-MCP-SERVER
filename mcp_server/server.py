import logging
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context

# Configure logger for protocol monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseworksMCPServer")

# ------------------------------------------------------------------------------
# 1. Server Initialization with Protocol Capability Negotiation
# ------------------------------------------------------------------------------
# FastMCP handles protocol negotiation during the initialize handshake.
# We explicitly document server-declared capabilities and create a client checker.

mcp = FastMCP(
    name="Pulseworks Marketing MCP Server",
    instructions=(
        "You are the Pulseworks Marketing Operations MCP Server. "
        "You manage scoped access to clients, campaigns, budgets, and ad copy."
    )
)

# Active session capability store
client_capabilities_store: Dict[str, Any] = {}


def get_declared_server_capabilities() -> Dict[str, Any]:
    """
    Returns the server capabilities declared to the client during initialize handshake.
    """
    return {
        "tools": {"listChanged": True},
        "resources": {"subscribe": False, "listChanged": True},
        "prompts": {"listChanged": True},
        "elicitation": {"supported": True},
        "logging": {}
    }


def check_client_capability(ctx: Optional[Context], capability_name: str) -> bool:
    """
    Safely inspects whether the connected MCP client declared support for a feature
    (e.g., 'elicitation', 'sampling') during initialization.
    
    Returns False if context/capabilities are absent, allowing tools to fallback safely.
    """
    if not ctx:
        logger.warning("No request context available. Assuming '%s' is unsupported.", capability_name)
        return False

    client_caps = getattr(ctx.session, "client_capabilities", {}) if hasattr(ctx, "session") else {}
    has_cap = client_caps.get(capability_name, False) or client_capabilities_store.get(capability_name, False)
    
    logger.info("Capability evaluation for '%s': %s", capability_name, has_cap)
    return bool(has_cap)


# ------------------------------------------------------------------------------
# 2. Diagnostic Tool for Capability Verification
# ------------------------------------------------------------------------------
@mcp.tool(
    name="check_system_capabilities",
    description="Inspects active protocol negotiation capabilities declared by the server and client."
)
async def check_system_capabilities(ctx: Context) -> dict:
    """
    Diagnostic tool to verify client/server capability exchange.
    """
    server_caps = get_declared_server_capabilities()
    client_supports_elicitation = check_client_capability(ctx, "elicitation")
    
    return {
        "status": "Negotiation Active",
        "server_capabilities": server_caps,
        "client_capabilities": {
            "elicitation_supported": client_supports_elicitation
        }
    }


if __name__ == "__main__":
    mcp.run()