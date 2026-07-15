import os


def backend_url() -> str:
    """Base URL of the Polingo HTTP API (read at call time for test overrides)."""
    return os.getenv("MCP_BACKEND_URL", "http://localhost:8000/api")


CONNECT_TIMEOUT_S = 5.0
MAX_RETRIES = 1
