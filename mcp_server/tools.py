from server import mcp

@mcp.tool()
def ping() -> str:
    """
    Health check tool.
    """
    return "pong"