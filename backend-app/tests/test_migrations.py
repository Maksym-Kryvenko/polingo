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


def test_gender_remap_defaults_legacy_meski_to_inanimate(tmp_path, monkeypatch):
    db = tmp_path / "gender.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0001_baseline")

    con = sqlite3.connect(db)
    con.execute("INSERT INTO word (polish, english, ukrainian, part_of_speech, gender) "
                "VALUES ('kot', 'cat', 'кіт', 'rzeczownik', 'męski')")
    con.commit()
    con.close()

    command.upgrade(cfg, "0002_gender_five_way")

    con = sqlite3.connect(db)
    gender = con.execute("SELECT gender FROM word WHERE polish='kot'").fetchone()[0]
    con.close()
    assert gender == "męskorzeczowy"


def test_pronoun_relabel_oni_one_to_oni(tmp_path, monkeypatch):
    db = tmp_path / "pron.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0002_gender_five_way")

    con = sqlite3.connect(db)
    con.execute("INSERT INTO word (polish, english, ukrainian, part_of_speech) "
                "VALUES ('robić', 'to do', 'робити', 'czasownik')")
    wid = con.execute("SELECT id FROM word WHERE polish='robić'").fetchone()[0]
    con.execute("INSERT INTO verbconjugation (word_id, pronoun, tense, conjugated_form) "
                "VALUES (?, 'oni/one', 'przeszły', 'robili')", (wid,))
    con.execute("INSERT INTO verbconjugation (word_id, pronoun, tense, conjugated_form) "
                "VALUES (?, 'oni/one', 'teraźniejszy', 'robią')", (wid,))
    con.commit()
    con.close()

    command.upgrade(cfg, "0003_pronoun_virility")

    con = sqlite3.connect(db)
    # past-tense row relabelled to virile oni, NOT duplicated as one
    past = con.execute("SELECT pronoun FROM verbconjugation "
                       "WHERE word_id=? AND tense='przeszły'", (wid,)).fetchall()
    # present-tense row relabelled to oni AND duplicated as one
    present = {r[0] for r in con.execute(
        "SELECT pronoun FROM verbconjugation WHERE word_id=? AND tense='teraźniejszy'",
        (wid,)).fetchall()}
    con.close()
    assert past == [("oni",)]
    assert present == {"oni", "one"}


def test_word_has_aspect_column_after_upgrade(tmp_path, monkeypatch):
    db = tmp_path / "aspect.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0004_word_aspect")

    con = sqlite3.connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(word)").fetchall()}
    con.close()
    assert "aspect" in cols


def test_attempt_table_created_at_0005(tmp_path, monkeypatch):
    db = tmp_path / "att.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0005_attempt_table")

    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    cols = {r[1] for r in con.execute("PRAGMA table_info(attempt)").fetchall()}
    con.close()

    assert "attempt" in names
    # old tables still present at this revision (dropped in 0006)
    assert "practicerecord" in names and "endingspracticerecord" in names
    assert {"word_id", "kind", "language_set", "direction", "part_of_speech",
            "was_correct", "user_answer", "correct_answer", "practice_date",
            "created_at"} <= cols


def test_data_copied_into_attempt_then_old_tables_dropped(tmp_path, monkeypatch):
    db = tmp_path / "copy.db"
    monkeypatch.setenv("POLINGO_DATABASE_URL", f"sqlite:///{db}")
    cfg = _alembic_cfg(str(db))
    command.upgrade(cfg, "0005_attempt_table")

    con = sqlite3.connect(db)
    con.execute("INSERT INTO word (polish, english, ukrainian, part_of_speech) "
                "VALUES ('kot', 'cat', 'кіт', 'rzeczownik')")
    wid = con.execute("SELECT id FROM word WHERE polish='kot'").fetchone()[0]
    con.execute("INSERT INTO practicerecord (word_id, language_set, direction, was_correct, "
                "user_answer, correct_answer, practice_date, created_at) "
                "VALUES (?, 'english', 'writing', 1, 'kot', 'kot', '2026-06-18', '2026-06-18 10:00:00')", (wid,))
    con.execute("INSERT INTO endingspracticerecord (word_id, part_of_speech, was_correct, "
                "user_answer, correct_answer, practice_date, created_at) "
                "VALUES (?, 'rzeczownik', 0, 'kota', 'kotu', '2026-06-18', '2026-06-18 11:00:00')", (wid,))
    con.commit()
    con.close()

    command.upgrade(cfg, "head")

    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    total = con.execute("SELECT COUNT(*) FROM attempt").fetchone()[0]
    practice = con.execute("SELECT COUNT(*) FROM attempt WHERE kind='practice'").fetchone()[0]
    endings = con.execute("SELECT COUNT(*) FROM attempt WHERE kind='endings'").fetchone()[0]
    con.close()

    assert total == 2 and practice == 1 and endings == 1
    assert "practicerecord" not in names and "endingspracticerecord" not in names
