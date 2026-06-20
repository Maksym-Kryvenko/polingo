from sqlalchemy.pool import StaticPool

from app import database


def test_in_memory_url_uses_static_pool():
    eng = database.make_engine("sqlite://")
    assert eng.pool.__class__ is StaticPool


def test_file_url_sets_busy_timeout():
    eng = database.make_engine("sqlite:///./tmp_timeout_test.db")
    assert eng.url.database == "./tmp_timeout_test.db"
    with eng.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
    assert result == 30000


def test_migration_is_idempotent_on_memory():
    # Memory DBs are skipped by the migrator; calling twice must not raise.
    database.init_db()
    database.init_db()


def test_healthz_via_client(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "polingo"}
