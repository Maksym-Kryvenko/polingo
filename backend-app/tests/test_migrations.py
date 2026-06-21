import pathlib
import sqlite3

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

_BACKEND_ROOT = pathlib.Path(__file__).resolve().parent.parent  # backend-app/


def _alembic_cfg(db_path: str) -> AlembicConfig:
    # Absolute paths so the test passes regardless of pytest's working directory.
    cfg = AlembicConfig(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


# xfail until Task 6 adds the final migrations — keeps the suite green for the
# intermediate commits. The marker is REMOVED in Task 6, Step 1.
@pytest.mark.xfail(reason="attempt table + table drop land in Task 6", strict=True)
def test_upgrade_head_builds_attempt_and_drops_old_tables(tmp_path, monkeypatch):
    db = tmp_path / "mig.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    command.upgrade(_alembic_cfg(str(db)), "head")

    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    con.close()

    assert "attempt" in names
    assert "practicerecord" not in names
    assert "endingspracticerecord" not in names
