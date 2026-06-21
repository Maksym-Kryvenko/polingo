WORD_KEYS = {"id", "polish", "english", "ukrainian", "part_of_speech", "gender"}


def test_words_initial_contract(seeded_client):
    resp = seeded_client.get("/api/words/initial?count=5")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 5
    assert WORD_KEYS <= set(body[0].keys())
    assert isinstance(body[0]["id"], int)
    # gender is volatile across Plan 2 (męski -> 5-gender); assert type only
    assert body[0]["gender"] is None or isinstance(body[0]["gender"], str)


def test_session_contract(seeded_client):
    resp = seeded_client.get("/api/session")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {"language_set", "words"}
    assert body["language_set"] in {"english", "ukrainian"}
    assert isinstance(body["words"], list)


def test_session_words_all_contract(seeded_client):
    resp = seeded_client.get("/api/session/words/all")
    assert resp.status_code == 200
    body = resp.json()
    assert "words" in body
    if body["words"]:
        w = body["words"][0]
        assert {"id", "polish", "total_attempts", "correct_attempts",
                "error_rate", "enabled"} <= set(w.keys())


def test_stats_contract(seeded_client):
    resp = seeded_client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "today_percentage", "trend", "overall_percentage", "available_words",
    }
    assert isinstance(body["available_words"], int)


def test_stats_history_contract(seeded_client):
    resp = seeded_client.get("/api/stats/history?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"records", "total"}
    assert isinstance(body["records"], list)
    assert isinstance(body["total"], int)
    # records may be empty on a fresh DB; do NOT assert record id values (Plan 2 changes them)


def test_endings_config_contract(seeded_client):
    resp = seeded_client.get("/api/endings/config")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"parts_of_speech", "cases", "tenses"}
    assert "rzeczownik" in body["parts_of_speech"]


def test_endings_stats_contract(seeded_client):
    resp = seeded_client.get("/api/endings/stats")
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {
        "today_percentage", "trend", "overall_percentage", "available_words",
    }


def test_admin_devices_contract(seeded_client):
    resp = seeded_client.get("/api/admin/devices")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"devices", "total_count", "active_count"}


def test_admin_settings_contract(seeded_client):
    resp = seeded_client.get("/api/admin/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    keys = {s["key"] for s in body}
    assert {"generate_on_the_fly", "tts_source"} <= keys


def test_admin_sentences_contract(seeded_client):
    resp = seeded_client.get("/api/admin/sentences")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_endings_question_404_on_empty_forms(seeded_client):
    # No declension/conjugation/sentence rows exist on a freshly-seeded DB
    # (fake_llm stubs form-gen to []), so the endpoint has no question to serve.
    # Freeze the 404 shape; a 200 contract is only testable once form-gen runs.
    resp = seeded_client.get("/api/endings/question?part_of_speech=rzeczownik")
    assert resp.status_code == 404
