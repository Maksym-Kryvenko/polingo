"""Env-driven settings. Functions (not constants) so values are read at call
time — this lets tests override behaviour with monkeypatch.setenv."""

import os


def database_url() -> str:
    return os.getenv("POLINGO_DATABASE_URL", "sqlite:////app/data/polingo.db")


def text_model() -> str:
    return os.getenv("POLINGO_TEXT_MODEL", "gpt-5-mini")


def stt_model() -> str:
    return os.getenv("POLINGO_STT_MODEL", "whisper-1")


def tts_model() -> str:
    return os.getenv("POLINGO_TTS_MODEL", "tts-1")


def tts_voice() -> str:
    return os.getenv("POLINGO_TTS_VOICE", "nova")
