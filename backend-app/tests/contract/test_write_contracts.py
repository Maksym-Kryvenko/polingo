def _first_word_id(seeded_client):
    return seeded_client.get("/api/words/initial?count=1").json()[0]["id"]


def test_practice_submit_contract(seeded_client):
    wid = _first_word_id(seeded_client)
    resp = seeded_client.post("/api/practice/submit", json={
        "word_id": wid, "language_set": "english",
        "direction": "writing", "was_correct": True,
    })
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {
        "today_percentage", "trend", "overall_percentage", "available_words",
    }


def test_practice_validate_contract(seeded_client):
    wid = _first_word_id(seeded_client)
    resp = seeded_client.post("/api/practice/validate", json={
        "word_id": wid, "language_set": "english",
        "direction": "writing", "answer": "something",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert {"was_correct", "correct_answer", "alternatives", "stats"} <= set(body.keys())
    assert isinstance(body["alternatives"], list)


def test_choose_translation_question_contract(seeded_client):
    resp = seeded_client.get(
        "/api/practice/choose-translation/question?language_set=english&direction=from_polish"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {"word_id", "prompt", "correct_answer", "options", "direction"} <= set(body.keys())
    assert isinstance(body["options"], list) and len(body["options"]) >= 2


def test_session_language_switch_contract(seeded_client):
    resp = seeded_client.put("/api/session/language", json={"language_set": "ukrainian"})
    assert resp.status_code == 200
    assert resp.json()["language_set"] == "ukrainian"


def test_session_add_word_contract(seeded_client):
    wid = _first_word_id(seeded_client)
    resp = seeded_client.post("/api/session/words", json={"word_id": wid})
    assert resp.status_code == 200
    assert "words" in resp.json()


def test_words_check_contract(seeded_client):
    resp = seeded_client.post("/api/words/check", json={"text": "kot"})
    assert resp.status_code == 200
    body = resp.json()
    assert {"found", "word", "matched_field", "created", "source"} <= set(body.keys())


def test_admin_setting_update_contract(seeded_client):
    resp = seeded_client.put("/api/admin/settings/tts_source", json={"value": "server"})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"key": "tts_source", "value": "server"}
