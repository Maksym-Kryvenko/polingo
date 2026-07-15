from enum import Enum

from worker.config import MAX_ATTEMPTS


class FormsStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


def next_status_on_success() -> FormsStatus:
    return FormsStatus.ready


def next_status_on_failure(attempt: int) -> FormsStatus:
    """attempt is 1-based. After MAX_ATTEMPTS, the word is terminally failed."""
    return FormsStatus.failed if attempt >= MAX_ATTEMPTS else FormsStatus.pending
