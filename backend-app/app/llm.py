from __future__ import annotations

import io
import json
import os
from functools import lru_cache
from typing import Any, Dict

from openai import OpenAI

from app import config
from app.models import PracticeDirection, WordLanguage


@lru_cache
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


# ── Word resolution ──────────────────────────────────────────


def resolve_word_via_llm(text: str) -> Dict[str, Any]:
    """Resolve a word/phrase: detect language, translate, determine part of speech."""
    client = get_openai_client()
    prompt = (
        "You are a careful linguist. Given a single word or short phrase in Polish, English, or Ukrainian, "
        "correct spelling if needed, provide translations in all three languages, and classify the "
        "part of speech of the POLISH form. "
        "Return JSON only with keys: detected_language, corrected_input, polish, english, ukrainian, "
        "part_of_speech (one of: rzeczownik, czasownik, przymiotnik, zaimek, przysłówek, inne), "
        "gender (for rzeczownik only: one of męskoosobowy [masc. personal], "
        "męskozywotny [masc. animate], męskorzeczowy [masc. inanimate], żeński, "
        "or nijaki; null otherwise), "
        "aspect (for czasownik only: dokonany or niedokonany; null otherwise). "
        "Use lowercase for translations unless proper noun."
    )
    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=f"Respond in JSON.\n{text}",
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return {
        "detected_language": str(payload.get("detected_language", "")),
        "corrected_input": str(payload.get("corrected_input", "")),
        "polish": str(payload.get("polish", "")),
        "english": str(payload.get("english", "")),
        "ukrainian": str(payload.get("ukrainian", "")),
        "part_of_speech": str(payload.get("part_of_speech", "inne")),
        "gender": payload.get("gender"),
        "aspect": payload.get("aspect"),
    }


# ── Translation validation ───────────────────────────────────


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
    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=f"Respond in JSON.\n{user_message}",
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return {
        "is_correct": bool(payload.get("is_correct")),
        "normalized_answer": str(payload.get("normalized_answer", "")),
        "rationale": str(payload.get("rationale", "")),
    }


# ── Pronunciation ────────────────────────────────────────────


def transcribe_audio(audio_data: bytes, filename: str = "audio.webm") -> str:
    client = get_openai_client()
    audio_file = io.BytesIO(audio_data)
    audio_file.name = filename
    response = client.audio.transcriptions.create(
        model=config.stt_model(),
        file=audio_file,
        language="pl",
    )
    return response.text.strip()


def evaluate_pronunciation_via_llm(
    *, expected_word: str, transcribed_text: str
) -> Dict[str, Any]:
    client = get_openai_client()
    prompt = (
        "You are a Polish language pronunciation evaluator. Compare the expected Polish word "
        "with what was transcribed from the learner's speech. Be lenient with capitalization and punctuation. "
        "Return JSON only with keys: is_correct (boolean), feedback (string), similarity_score (float 0-1)."
    )
    user_message = (
        f"Expected Polish word: {expected_word}\n"
        f"Transcribed speech: {transcribed_text}"
    )
    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=f"Respond in JSON.\n{user_message}",
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return {
        "is_correct": bool(payload.get("is_correct")),
        "feedback": str(payload.get("feedback", "")),
        "similarity_score": float(payload.get("similarity_score", 0.0)),
    }


# ── Verb conjugation generation ──────────────────────────────


def generate_verb_conjugations_via_llm(
    polish_infinitive: str, tenses: list[str] | None = None
) -> Dict[str, Any]:
    """Generate Polish verb conjugations for specified tenses."""
    if tenses is None:
        tenses = ["teraźniejszy", "przeszły", "przyszły"]

    client = get_openai_client()
    tenses_str = ", ".join(tenses)
    prompt = (
        "You are a Polish language expert. Given a Polish verb infinitive, generate conjugations "
        f"for the following tenses: {tenses_str}. "
        "Return JSON with key 'conjugations' which is an object where each key is a tense name "
        "and each value is an object with pronoun keys (ja, ty, on_ona_ono, my, wy, oni, one) "
        "mapping to the conjugated Polish form. "
        "For past tense, use masculine forms for ja/ty/on and feminine for ona; "
        "'oni' is the męskoosobowy (virile) plural form (e.g. robili) and 'one' is the "
        "niemęskoosobowy (non-virile) plural form (e.g. robiły). "
        "For present and future tense, 'oni' and 'one' take IDENTICAL forms — return the "
        "same conjugated form under both keys (e.g. oni robią / one robią). "
        "For future tense of imperfective verbs, use 'będę + infinitive' pattern. "
        "For perfective verbs, conjugate in the present form (which has future meaning)."
    )
    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=f"Respond in JSON.\nVerb: {polish_infinitive}",
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return payload.get("conjugations", {})


# ── Noun/Adjective declension generation ─────────────────────


def generate_declensions_via_llm(
    polish_word: str, part_of_speech: str, gender: str | None = None
) -> list[dict]:
    """Generate all 7 case declensions for a noun or adjective.
    Returns list of dicts: {case, gender, number, form}.
    """
    client = get_openai_client()

    if part_of_speech == "rzeczownik":
        prompt = (
            "You are a Polish language expert. Given a Polish noun and its grammatical gender, "
            "generate all 7 case forms (mianownik, dopełniacz, celownik, biernik, narzędnik, "
            "miejscownik, wołacz) for both singular and plural. "
            "Return JSON with key 'forms' which is an array of objects, each with: "
            "case (string), gender (string - the noun's gender), number ('singular' or 'plural'), form (string). "
            f"The noun's gender is: {gender or 'unknown (please determine it)'}."
        )
    else:  # przymiotnik
        prompt = (
            "You are a Polish language expert. Given a Polish adjective, "
            "generate all 7 case forms (mianownik, dopełniacz, celownik, biernik, narzędnik, "
            "miejscownik, wołacz) for all five genders (męskoosobowy, męskozywotny, "
            "męskorzeczowy, żeński, nijaki) "
            "in both singular and plural. "
            "Return JSON with key 'forms' which is an array of objects, each with: "
            "case (string), gender (string), number ('singular' or 'plural'), form (string)."
        )

    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=f"Respond in JSON.\nWord: {polish_word}",
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return payload.get("forms", [])


# ── Practice sentence generation ─────────────────────────────


def generate_practice_sentences_via_llm(
    polish_word: str,
    part_of_speech: str,
    forms: list[dict],
) -> list[dict]:
    """Generate simple practice sentences for each form of a word.

    *forms* contains declension/conjugation data.
    Returns list of dicts with: sentence, correct_answer, case/gender/number/pronoun/tense.
    """
    client = get_openai_client()

    forms_json = json.dumps(forms, ensure_ascii=False)

    if part_of_speech == "czasownik":
        prompt = (
            "You are a Polish language teacher. Given a Polish verb and its conjugated forms, "
            "create a simple Polish sentence for EACH form where the conjugated verb is replaced by ___. "
            "The sentence should make it clear which pronoun and tense is expected. "
            "Include the pronoun in the sentence. "
            "Return JSON with key 'sentences' — an array of objects with: "
            "sentence (string with ___), correct_answer (string), pronoun (string), tense (string). "
            "Keep sentences short and natural (5-8 words)."
        )
    else:
        prompt = (
            "You are a Polish language teacher. Given a Polish word and its declined forms, "
            "create a simple Polish sentence for EACH form where the declined word is replaced by ___. "
            "The sentence should make it clear which case/gender/number is expected from context. "
            "Return JSON with key 'sentences' — an array of objects with: "
            "sentence (string with ___), correct_answer (string), "
            "case (string), gender (string), number (string). "
            "Keep sentences short and natural (5-8 words)."
        )

    user_message = f"Respond in JSON.\nWord: {polish_word}\nPart of speech: {part_of_speech}\nForms:\n{forms_json}"

    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=user_message,
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return payload.get("sentences", [])


def generate_sentence_on_the_fly(
    polish_word: str,
    part_of_speech: str,
    *,
    case: str | None = None,
    gender: str | None = None,
    number: str | None = None,
    pronoun: str | None = None,
    tense: str | None = None,
) -> Dict[str, Any]:
    """Generate a single practice sentence on-the-fly (used when admin toggle is on)."""
    client = get_openai_client()

    context_parts = []
    if case:
        context_parts.append(f"case: {case}")
    if gender:
        context_parts.append(f"gender: {gender}")
    if number:
        context_parts.append(f"number: {number}")
    if pronoun:
        context_parts.append(f"pronoun: {pronoun}")
    if tense:
        context_parts.append(f"tense: {tense}")
    context_str = ", ".join(context_parts)

    prompt = (
        "You are a Polish language teacher. Create a simple Polish sentence using the given word "
        "in the specified grammatical form. Replace the target word form with ___. "
        "Also provide the correct answer (the word in the required form) and 3 plausible but wrong alternatives. "
        "Return JSON with keys: sentence (string with ___), correct_answer (string), "
        "wrong_options (array of 3 strings)."
    )
    user_message = (
        f"Respond in JSON.\nWord: {polish_word}\nPart of speech: {part_of_speech}\n"
        f"Required form: {context_str}"
    )

    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=user_message,
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    payload: Dict[str, Any] = json.loads(content)
    return {
        "sentence": str(payload.get("sentence", "")),
        "correct_answer": str(payload.get("correct_answer", "")),
        "wrong_options": payload.get("wrong_options", []),
    }


def fix_sentence_via_llm(
    sentence: str,
    correct_answer: str,
    polish_word: str,
    part_of_speech: str,
) -> Dict[str, Any]:
    """Ask LLM to review and fix a practice sentence."""
    client = get_openai_client()

    prompt = (
        "You are a Polish language expert. Review this practice sentence and fix any grammatical, "
        "spelling, or contextual errors. The sentence has a ___ placeholder for the answer. "
        "Make sure the sentence is natural Polish, the correct_answer fits grammatically, and the "
        "blank placement makes sense. Return JSON with keys: sentence (fixed string with ___), "
        "correct_answer (fixed string)."
    )
    user_message = (
        f"Respond in JSON.\nWord: {polish_word}\nPart of speech: {part_of_speech}\n"
        f"Sentence: {sentence}\nCorrect answer: {correct_answer}"
    )

    response = client.responses.create(
        model=config.text_model(),
        instructions=prompt,
        input=user_message,
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text or "{}"
    data: Dict[str, Any] = json.loads(content)
    return {
        "sentence": str(data.get("sentence", sentence)),
        "correct_answer": str(data.get("correct_answer", correct_answer)),
    }


# ── Text-to-speech ───────────────────────────────────────────


def text_to_speech(text: str) -> bytes:
    """Generate speech audio for a Polish text using OpenAI TTS."""
    client = get_openai_client()
    response = client.audio.speech.create(
        model=config.tts_model(),
        voice=config.tts_voice(),
        input=text,
        response_format="mp3",
    )
    return response.content
