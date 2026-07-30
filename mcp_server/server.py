from pathlib import Path
import sqlite3
from contextlib import contextmanager

from dotenv import load_dotenv
from fastmcp import FastMCP

import os

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

# -----------------------------
# Create MCP server
# -----------------------------
mcp = FastMCP(
    name="Pulseworks Marketing MCP Server"
)

# -----------------------------
# Database configuration
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        BASE_DIR / "db" / "marketing.db"
    )
)

# -----------------------------
# Database helper
# -----------------------------
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()


# -----------------------------
# Temporary test tool
# -----------------------------
@mcp.tool()
def hello() -> str:
    """
    Simple tool used to verify that the MCP server is running.
    """
    return "Hello from Pulseworks Marketing MCP Server!"


# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":
    mcp.run()