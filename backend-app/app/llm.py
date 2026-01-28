from __future__ import annotations

import io
import json
import os
from functools import lru_cache
from typing import Any, Dict

from openai import OpenAI

from app.models import PracticeDirection, WordLanguage


@lru_cache
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def resolve_word_via_llm(text: str) -> Dict[str, str]:
    client = get_openai_client()
    prompt = (
        "You are a careful linguist. Given a single word or short phrase in Polish, English, or Ukrainian, "
        "correct spelling if needed and provide translations in the other two languages. "
        "Return JSON only with keys: detected_language, corrected_input, polish, english, ukrainian. "
        "Use lowercase for the translations unless proper noun."
    )
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return {
        "detected_language": str(payload.get("detected_language", "")),
        "corrected_input": str(payload.get("corrected_input", "")),
        "polish": str(payload.get("polish", "")),
        "english": str(payload.get("english", "")),
        "ukrainian": str(payload.get("ukrainian", "")),
    }


def validate_translation_via_llm(
    *,
    polish: str,
    answer: str,
    direction: PracticeDirection,
    target_language: WordLanguage,
    expected: str,
) -> Dict[str, Any]:
    client = get_openai_client()
    prompt = (
        "You are a strict language evaluator. Decide if the learner answer is a valid translation "
        "for the given Polish term. If the answer is correct but slightly off in spelling, return the corrected form. "
        "Return JSON only with keys: is_correct (boolean), normalized_answer (string), rationale (string)."
    )
    user_message = (
        f"Polish term: {polish}\n"
        f"Expected ({target_language.value}) hint: {expected}\n"
        f"Direction: {direction.value}\n"
        f"Learner answer ({target_language.value}): {answer}"
    )
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return {
        "is_correct": bool(payload.get("is_correct")),
        "normalized_answer": str(payload.get("normalized_answer", "")),
        "rationale": str(payload.get("rationale", "")),
    }


def transcribe_audio(audio_data: bytes, filename: str = "audio.webm") -> str:
    """Transcribe audio using OpenAI Whisper API."""
    client = get_openai_client()

    audio_file = io.BytesIO(audio_data)
    audio_file.name = filename

    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="pl",
    )
    return response.text.strip()


def evaluate_pronunciation_via_llm(
    *,
    expected_word: str,
    transcribed_text: str,
) -> Dict[str, Any]:
    """Evaluate if the transcribed pronunciation matches the expected word."""
    client = get_openai_client()

    prompt = (
        "You are a Polish language pronunciation evaluator. Compare the expected Polish word "
        "with what was transcribed from the learner's speech. Consider that speech-to-text "
        "may have minor variations. Be lenient with capitalization and punctuation. "
        "Return JSON only with keys: is_correct (boolean), feedback (string with helpful pronunciation tips if incorrect), "
        "similarity_score (float 0-1 indicating how close the pronunciation was)."
    )

    user_message = (
        f"Expected Polish word: {expected_word}\n"
        f"Transcribed speech: {transcribed_text}"
    )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    payload: Dict[str, Any] = json.loads(content)

    return {
        "is_correct": bool(payload.get("is_correct")),
        "feedback": str(payload.get("feedback", "")),
        "similarity_score": float(payload.get("similarity_score", 0.0)),
    }


def generate_verb_conjugations_via_llm(
    verb: str, source_language: str
) -> Dict[str, Any]:
    """Generate Polish verb conjugations from English or Ukrainian input."""
    client = get_openai_client()

    prompt = (
        "You are a Polish language expert. Given a verb in English or Ukrainian, "
        "provide the Polish infinitive and all present tense conjugations. "
        "Return JSON only with keys: "
        "infinitive (Polish infinitive form), "
        "english (English translation), "
        "ukrainian (Ukrainian translation), "
        "conjugations (object with keys: ja, ty, on_ona_ono, my, wy, oni_one - each containing the conjugated Polish form). "
        'Example for \'to do\': {"infinitive": "robić", "english": "to do", "ukrainian": "робити", '
        '"conjugations": {"ja": "robię", "ty": "robisz", "on_ona_ono": "robi", "my": "robimy", "wy": "robicie", "oni_one": "robią"}}'
    )

    user_message = f"Verb ({source_language}): {verb}"

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    payload: Dict[str, Any] = json.loads(content)

    return {
        "infinitive": str(payload.get("infinitive", "")),
        "english": str(payload.get("english", "")),
        "ukrainian": str(payload.get("ukrainian", "")),
        "conjugations": payload.get("conjugations", {}),
    }
