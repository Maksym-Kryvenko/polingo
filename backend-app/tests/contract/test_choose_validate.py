def _first_word_id(seeded_client):
    return seeded_client.get("/api/words/initial?count=1").json()[0]["id"]


def test_choose_translation_validate_from_polish(seeded_client):
    wid = _first_word_id(seeded_client)
    resp = seeded_client.post("/api/practice/choose-translation/validate", json={
        "word_id": wid, "language_set": "english",
        "direction": "from_polish", "answer": "whatever",
    })
    assert resp.status_code == 200, resp.text


def test_choose_translation_validate_to_polish(seeded_client):
    wid = _first_word_id(seeded_client)
    resp = seeded_client.post("/api/practice/choose-translation/validate", json={
        "word_id": wid, "language_set": "english",
        "direction": "to_polish", "answer": "whatever",
    })
    assert resp.status_code == 200, resp.text


def test_full_choose_chain_from_polish(seeded_client):
    """Mirror the exact frontend sequence: fetch question, then validate
    using the returned word_id + same language_set + direction."""
    q = seeded_client.get(
        "/api/practice/choose-translation/question?language_set=english&direction=from_polish"
    )
    assert q.status_code == 200, q.text
    body = q.json()
    resp = seeded_client.post("/api/practice/choose-translation/validate", json={
        "word_id": body["word_id"], "language_set": "english",
        "direction": "from_polish", "answer": body["options"][0],
    })
    assert resp.status_code == 200, resp.text


def test_full_choose_chain_to_polish(seeded_client):
    q = seeded_client.get(
        "/api/practice/choose-translation/question?language_set=english&direction=to_polish"
    )
    assert q.status_code == 200, q.text
    body = q.json()
    resp = seeded_client.post("/api/practice/choose-translation/validate", json={
        "word_id": body["word_id"], "language_set": "english",
        "direction": "to_polish", "answer": body["options"][0],
    })
    assert resp.status_code == 200, resp.text
