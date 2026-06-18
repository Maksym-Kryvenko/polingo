import inspect

from app import config, llm


def test_llm_has_no_hardcoded_model_constant():
    # MODEL must be gone; ids come from config now.
    assert not hasattr(llm, "MODEL")


def test_text_model_is_config_driven(monkeypatch):
    monkeypatch.setenv("POLINGO_TEXT_MODEL", "gpt-from-env")
    assert config.text_model() == "gpt-from-env"


def test_llm_source_references_config_text_model():
    src = inspect.getsource(llm)
    assert "config.text_model()" in src
    assert '"gpt-5-mini"' not in src  # no hard-coded id left in llm.py
