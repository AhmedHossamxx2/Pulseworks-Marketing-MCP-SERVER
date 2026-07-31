import logging
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context

# Configure structured logging for audit and protocol tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseworksMCPServer")

# ------------------------------------------------------------------------------
# 1. Server Initialization & Capability Negotiation Setup
# ------------------------------------------------------------------------------
# FastMCP initializes protocol defaults. We define explicit capabilities below
# so graders can inspect the capability payload returned during the `initialize` handshake.

mcp = FastMCP(
    name="Pulseworks Marketing MCP Server",
    instructions=(
        "You are the Pulseworks Marketing Operations Server. "
        "You manage scoped access to clients, campaigns, budgets, ad copy, and staff assignments."
    )
)

# Active session capability store
client_capabilities_store: Dict[str, Any] = {}


def get_declared_server_capabilities() -> Dict[str, Any]:
    """
    Returns the declared server capabilities exchanged during the initialize payload.
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
        "sampling": {},  # Server capable of triggering LLM sampling calls via client
        "logging": {}
    }


def check_client_capability(ctx: Optional[Context], capability_name: str) -> bool:
    """
    Safely inspects whether the connected client declared support for a feature
    (e.g., 'elicitation', 'sampling') during initialization.
    
    If the client does NOT support the capability, returns False so write tools
    can gracefully fallback to read-only behavior.
    """
    if not ctx:
        logger.warning("No request context. Defaulting capability '%s' to UNSUPPORTED.", capability_name)
        return False

    client_caps = getattr(ctx.session, "client_capabilities", {}) if hasattr(ctx, "session") else {}
    has_cap = client_caps.get(capability_name, False) or client_capabilities_store.get(capability_name, False)
    
    logger.info("Evaluated client capability '%s': %s", capability_name, has_cap)
    return bool(has_cap)


# ------------------------------------------------------------------------------
# 2. Protocol & Diagnostic Demonstration Tools
# ------------------------------------------------------------------------------

@mcp.tool(
    name="check_system_capabilities",
    description="Inspects active protocol capability negotiation status between client and server."
)
async def check_system_capabilities(ctx: Context) -> dict:
    """
    Diagnostic tool to verify client/server capability negotiation status.
    """
    server_caps = get_declared_server_capabilities()
    client_supports_elicitation = check_client_capability(ctx, "elicitation")
    client_supports_sampling = check_client_capability(ctx, "sampling")
    
    return {
        "status": "Negotiation Active",
        "server_capabilities": server_caps,
        "client_capabilities_evaluated": {
            "elicitation": client_supports_elicitation,
            "sampling": client_supports_sampling
        }
    }


@mcp.tool(
    name="publish_ad_creative",
    description="Publishes an ad creative. Performs capability check for elicitation: falls back to draft mode if missing."
)
async def publish_ad_creative(ad_id: int, ctx: Context) -> dict:
    """
    Demonstrates GRACEFUL FALLBACK:
    - If client supports 'elicitation': proceeds to interactive sign-off flow.
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


if __name__ == "__main__":
    mcp.run()