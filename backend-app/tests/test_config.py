from app import config


def test_database_url_defaults_to_container_path(monkeypatch):
    monkeypatch.delenv("POLINGO_DATABASE_URL", raising=False)
    assert config.database_url() == "sqlite:////app/data/polingo.db"


def test_database_url_reads_env_at_call_time(monkeypatch):
    monkeypatch.setenv("POLINGO_DATABASE_URL", "sqlite:///./custom.db")
    assert config.database_url() == "sqlite:///./custom.db"


def test_text_model_default_and_override(monkeypatch):
    monkeypatch.delenv("POLINGO_TEXT_MODEL", raising=False)
    assert config.text_model() == "gpt-5-mini"
    monkeypatch.setenv("POLINGO_TEXT_MODEL", "gpt-test")
    assert config.text_model() == "gpt-test"


def test_audio_model_defaults(monkeypatch):
    monkeypatch.delenv("POLINGO_STT_MODEL", raising=False)
    monkeypatch.delenv("POLINGO_TTS_MODEL", raising=False)
    monkeypatch.delenv("POLINGO_TTS_VOICE", raising=False)
    assert config.stt_model() == "whisper-1"
    assert config.tts_model() == "tts-1"
    assert config.tts_voice() == "nova"
