from worker.status import FormsStatus, next_status_on_success, next_status_on_failure


def test_success_goes_ready():
    assert next_status_on_success() == FormsStatus.ready


def test_failure_under_max_stays_pending():
    assert next_status_on_failure(attempt=1) == FormsStatus.pending


def test_failure_at_max_goes_failed():
    assert next_status_on_failure(attempt=3) == FormsStatus.failed
