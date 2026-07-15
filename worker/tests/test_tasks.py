import pytest

from worker.status import FormsStatus
from worker.tasks import generate_forms


@pytest.mark.asyncio
async def test_generate_forms_marks_ready_on_success():
    calls = {}

    async def fake_generate(word_id):
        calls["id"] = word_id
        return {"declensions": 7}

    async def fake_set_status(word_id, status):
        calls["status"] = status

    result = await generate_forms(
        {}, word_id=99, generate_fn=fake_generate, set_status_fn=fake_set_status
    )
    assert calls["id"] == 99
    assert calls["status"] == FormsStatus.ready
    assert result["status"] == FormsStatus.ready.value


@pytest.mark.asyncio
async def test_generate_forms_marks_failed_on_final_attempt():
    statuses = []

    async def boom(word_id):
        raise RuntimeError("llm down")

    async def fake_set_status(word_id, status):
        statuses.append(status)

    with pytest.raises(RuntimeError):
        await generate_forms(
            {"job_try": 3}, word_id=99, generate_fn=boom, set_status_fn=fake_set_status
        )
    assert statuses[-1] == FormsStatus.failed
