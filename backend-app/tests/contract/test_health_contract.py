def test_healthz_contract(seeded_client):
    resp = seeded_client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"status", "service"}
    assert body["status"] == "ok"
