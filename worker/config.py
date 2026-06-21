import os

MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 5
STUCK_AFTER_S = 600  # 10 min with no active job → re-enqueue


def redis_url() -> str:
    return os.getenv("POLINGO_REDIS_URL", "redis://localhost:6379")
