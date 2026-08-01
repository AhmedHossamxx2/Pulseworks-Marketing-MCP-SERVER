import os
from dotenv import load_dotenv

load_dotenv()


def str_to_bool(value: str | None) -> bool:
    if not value:
        return False
    return value.lower() in ("true", "1", "yes")


class Config:
    USE_MOCK = str_to_bool(os.getenv("USE_MOCK", "true"))
    DEBUG = str_to_bool(os.getenv("DEBUG", "false"))

    MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.6-flash")

    GEMINI_API_KEY = (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    )

    MCP_TRANSPORT_TYPE = os.getenv("MCP_TRANSPORT_TYPE", "stdio")
    MCP_SERVER_COMMAND = os.getenv(
        "MCP_SERVER_COMMAND", "python ../mcp_server/server.py"
    )
    MCP_SERVER_HTTP_URL = os.getenv(
        "MCP_SERVER_HTTP_URL", "http://localhost:8000/sse"
    )

    @classmethod
    def validate(cls):
        if not cls.GEMINI_API_KEY:
            raise ValueError("Missing GEMINI_API_KEY in environment variables")

        if cls.MCP_TRANSPORT_TYPE == "http" and not cls.MCP_SERVER_HTTP_URL:
            raise ValueError("Missing MCP_SERVER_HTTP_URL for HTTP transport")


config = Config()
config.validate()