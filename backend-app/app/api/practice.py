import random

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select

from app.database import engine
from app.llm import (
    validate_translation_via_llm,
    transcribe_audio,
    evaluate_pronunciation_via_llm,
)
from app.models import (
    PracticeRecord,
    PracticeDirection,
    Word,
    WordLanguage,
    WordOption,
    UserSession,
    UserSessionWord,
)
from app.schemas import (
    PracticeSubmission,
    PracticeValidationRequest,
    PracticeValidationResponse,
    PronunciationValidationResponse,
    StatsResponse,
    TranslationQuestion,
    TranslationValidationRequest,
    TranslationValidationResponse,
)
from app.utils import calculate_stats, normalize_text

router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/submit", response_model=StatsResponse)
def submit_practice(payload: PracticeSubmission) -> StatsResponse:
    with Session(engine) as session:
        session.add(PracticeRecord(**payload.model_dump()))
        session.commit()
        return calculate_stats(session)


def get_target_language(
    direction: PracticeDirection, language_set: str
) -> WordLanguage:
    if direction == PracticeDirection.writing:
        return WordLanguage.polish
    return WordLanguage(language_set)


@router.post("/validate", response_model=PracticeValidationResponse)
def validate_practice(payload: PracticeValidationRequest) -> PracticeValidationResponse:
    with Session(engine) as session:
        word = session.get(Word, payload.word_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        expected = (
            word.polish
            if payload.direction == PracticeDirection.writing
            else getattr(word, payload.language_set)
        )

        target_language = get_target_language(payload.direction, payload.language_set)
        options = session.exec(
            select(WordOption).where(
                WordOption.word_id == word.id,
                WordOption.language == target_language,
            )
        ).all()
        accepted_answers = [expected] + [option.value for option in options]

        normalized_answer = normalize_text(payload.answer)
        matched_via = None
        is_correct = False
        for answer in accepted_answers:
            if normalize_text(answer) == normalized_answer:
                is_correct = True
                matched_via = "option" if answer != expected else "direct"
                break

        if not is_correct:
            try:
                llm_validation = validate_translation_via_llm(
                    polish=word.polish,
                    answer=payload.answer,
                    direction=payload.direction,
                    target_language=target_language,
                    expected=expected,
                )
            except RuntimeError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            if llm_validation.get("is_correct"):
                corrected = llm_validation.get("normalized_answer") or payload.answer
                is_correct = True
                matched_via = "llm"
                exists = session.exec(
                    select(WordOption).where(
                        WordOption.word_id == word.id,
                        WordOption.language == target_language,
                        WordOption.value == corrected,
                    )
                ).first()
                if not exists:
                    session.add(
                        WordOption(
                            word_id=word.id,
                            language=target_language,
                            value=corrected,
                        )
                    )
                    session.commit()

        session.add(
            PracticeRecord(
                word_id=word.id,
                language_set=payload.language_set,
                direction=payload.direction,
                was_correct=is_correct,
            )
        )
        session.commit()

        # Get all alternatives for display
        alternatives = [opt.value for opt in options if opt.value != expected]

        return PracticeValidationResponse(
            was_correct=is_correct,
            correct_answer=expected,
            matched_via=matched_via,
            alternatives=alternatives,
            stats=calculate_stats(session),
        )


@router.post("/skip", response_model=PracticeValidationResponse)
def skip_practice(payload: PracticeValidationRequest) -> PracticeValidationResponse:
    """Skip a word and record it as incorrect."""
    with Session(engine) as session:
        word = session.get(Word, payload.word_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        expected = (
            word.polish
            if payload.direction == PracticeDirection.writing
            else getattr(word, payload.language_set)
        )

        target_language = get_target_language(payload.direction, payload.language_set)
        options = session.exec(
            select(WordOption).where(
                WordOption.word_id == word.id,
                WordOption.language == target_language,
            )
        ).all()

        session.add(
            PracticeRecord(
                word_id=word.id,
                language_set=payload.language_set,
                direction=payload.direction,
                was_correct=False,
            )
        )
        session.commit()

        alternatives = [opt.value for opt in options if opt.value != expected]

        return PracticeValidationResponse(
            was_correct=False,
            correct_answer=expected,
            matched_via=None,
            alternatives=alternatives,
            stats=calculate_stats(session),
        )


@router.post("/pronunciation", response_model=PronunciationValidationResponse)
async def validate_pronunciation(
    audio: UploadFile = File(...),
    word_id: int = Form(...),
    language_set: str = Form(...),
) -> PronunciationValidationResponse:
    """Validate pronunciation of a Polish word using OpenAI Whisper and GPT."""
    with Session(engine) as session:
        word = session.get(Word, word_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        try:
            audio_data = await audio.read()
            transcribed_text = transcribe_audio(
                audio_data, audio.filename or "audio.webm"
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Audio transcription failed: {str(exc)}"
            ) from exc

        try:
            evaluation = evaluate_pronunciation_via_llm(
                expected_word=word.polish,
                transcribed_text=transcribed_text,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        is_correct = evaluation["is_correct"]

        session.add(
            PracticeRecord(
                word_id=word.id,
                language_set=language_set,
                direction=PracticeDirection.pronunciation,
                was_correct=is_correct,
            )
        )
        session.commit()

        return PronunciationValidationResponse(
            was_correct=is_correct,
            expected_word=word.polish,
            transcribed_text=transcribed_text,
            feedback=evaluation["feedback"],
            similarity_score=evaluation["similarity_score"],
            stats=calculate_stats(session),
        )


@router.get("/choose-translation/question", response_model=TranslationQuestion)
def get_translation_question(
    language_set: str = "english", direction: str = "from_polish"
) -> TranslationQuestion:
    """Get a random translation question with 4 options from session words."""
    with Session(engine) as session:
        user_session = session.exec(select(UserSession)).first()
        if not user_session:
            raise HTTPException(status_code=400, detail="No session found")

        session_words = session.exec(
            select(UserSessionWord).where(
                UserSessionWord.session_id == user_session.id,
                UserSessionWord.enabled == True,
            )
        ).all()

        if len(session_words) < 4:
            raise HTTPException(
                status_code=400,
                detail="Need at least 4 words in session for this practice mode.",
            )

        # Pick a random word as the question
        random_sw = random.choice(session_words)
        target_word = session.get(Word, random_sw.word_id)
        if not target_word:
            raise HTTPException(status_code=404, detail="Word not found")

        # Determine prompt and correct answer based on direction
        if direction == "from_polish":
            # Show Polish, choose English/Ukrainian
            prompt = target_word.polish
            correct_answer = getattr(target_word, language_set)
        else:
            # Show English/Ukrainian, choose Polish
            prompt = getattr(target_word, language_set)
            correct_answer = target_word.polish

        # Get other words for wrong options
        other_session_words = [
            sw for sw in session_words if sw.word_id != target_word.id
        ]
        random.shuffle(other_session_words)

        wrong_options = []
        for sw in other_session_words[:3]:
            word = session.get(Word, sw.word_id)
            if word:
                if direction == "from_polish":
                    wrong_options.append(getattr(word, language_set))
                else:
                    wrong_options.append(word.polish)

        # Create options and shuffle
        options = [correct_answer] + wrong_options
        random.shuffle(options)

        return TranslationQuestion(
            word_id=target_word.id,
            polish=target_word.polish,
            english=target_word.english,
            ukrainian=target_word.ukrainian,
            prompt=prompt,
            correct_answer=correct_answer,
            options=options,
            direction=direction,
        )


@router.post(
    "/choose-translation/validate", response_model=TranslationValidationResponse
)
def validate_translation_choice(
    payload: TranslationValidationRequest,
) -> TranslationValidationResponse:
    """Validate a translation choice answer."""
    with Session(engine) as session:
        word = session.get(Word, payload.word_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")

        # Determine correct answer based on direction
        if payload.direction == "from_polish":
            correct_answer = getattr(word, payload.language_set)
        else:
            correct_answer = word.polish

        # Check if answer is correct (exact match for multiple choice)
        is_correct = normalize_text(payload.answer) == normalize_text(correct_answer)

        # Determine practice direction for recording
        practice_direction = (
            PracticeDirection.translation
            if payload.direction == "from_polish"
            else PracticeDirection.writing
        )

        session.add(
            PracticeRecord(
                word_id=word.id,
                language_set=payload.language_set,
                direction=practice_direction,
                was_correct=is_correct,
            )
        )
        session.commit()

        return TranslationValidationResponse(
            was_correct=is_correct,
            correct_answer=correct_answer,
            stats=calculate_stats(session),
        )
