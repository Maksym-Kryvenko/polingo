import threading

from sqlalchemy import func
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models import (
    Word,
    UserSession,
    UserSessionWord,
    PartOfSpeech,
    VerbConjugation,
    WordDeclension,
    PracticeSentence,
    GrammaticalCase,
    GrammaticalGender,
    GrammaticalNumber,
    VerbTense,
    Pronoun,
)
from app.schemas import (
    WordCheckRequest,
    WordCheckResponse,
    WordCheckBulkRequest,
    WordCheckBulkResponse,
    WordCheckResult,
    WordRead,
    WordUpdateRequest,
)
from app.llm import (
    resolve_word_via_llm,
    generate_declensions_via_llm,
    generate_verb_conjugations_via_llm,
    generate_practice_sentences_via_llm,
)

router = APIRouter(prefix="/words", tags=["words"])

PRONOUN_MAP = {
    "ja": Pronoun.ja,
    "ty": Pronoun.ty,
    "on_ona_ono": Pronoun.on_ona_ono,
    "my": Pronoun.my,
    "wy": Pronoun.wy,
    "oni_one": Pronoun.oni_one,
}


def _generate_forms_background(word_id: int, polish: str, part_of_speech: str, gender: str | None):
    """Generate declensions/conjugations & practice sentences in background."""
    try:
        forms_for_sentences = []

        if part_of_speech in ("rzeczownik", "przymiotnik"):
            raw_forms = generate_declensions_via_llm(polish, part_of_speech, gender)
            with Session(engine) as session:
                for f in raw_forms:
                    case_val = f.get("case", "")
                    gender_val = f.get("gender", gender or "")
                    number_val = f.get("number", "singular")
                    form_val = f.get("form", "")
                    if not form_val or not case_val:
                        continue
                    try:
                        case_enum = GrammaticalCase(case_val)
                        gender_enum = GrammaticalGender(gender_val)
                        number_enum = GrammaticalNumber(number_val)
                    except ValueError:
                        continue
                    existing = session.exec(
                        select(WordDeclension).where(
                            WordDeclension.word_id == word_id,
                            WordDeclension.case == case_enum,
                            WordDeclension.gender == gender_enum,
                            WordDeclension.number == number_enum,
                        )
                    ).first()
                    if not existing:
                        session.add(WordDeclension(
                            word_id=word_id,
                            case=case_enum,
                            gender=gender_enum,
                            number=number_enum,
                            form=form_val,
                        ))
                    forms_for_sentences.append(f)
                session.commit()

        elif part_of_speech == "czasownik":
            raw_conjugations = generate_verb_conjugations_via_llm(polish)
            with Session(engine) as session:
                for tense_name, pronouns in raw_conjugations.items():
                    if not isinstance(pronouns, dict):
                        continue
                    try:
                        tense_enum = VerbTense(tense_name)
                    except ValueError:
                        continue
                    for pronoun_key, form_val in pronouns.items():
                        if not form_val:
                            continue
                        pronoun_enum = PRONOUN_MAP.get(pronoun_key)
                        if not pronoun_enum:
                            continue
                        existing = session.exec(
                            select(VerbConjugation).where(
                                VerbConjugation.word_id == word_id,
                                VerbConjugation.pronoun == pronoun_enum,
                                VerbConjugation.tense == tense_enum,
                            )
                        ).first()
                        if not existing:
                            session.add(VerbConjugation(
                                word_id=word_id,
                                pronoun=pronoun_enum,
                                tense=tense_enum,
                                conjugated_form=form_val,
                            ))
                        forms_for_sentences.append({
                            "pronoun": pronoun_key,
                            "tense": tense_name,
                            "form": form_val,
                        })
                session.commit()

        # Generate practice sentences
        if forms_for_sentences:
            raw_sentences = generate_practice_sentences_via_llm(
                polish, part_of_speech, forms_for_sentences
            )
            with Session(engine) as session:
                pos_enum = PartOfSpeech(part_of_speech)
                for s in raw_sentences:
                    sentence_text = s.get("sentence", "")
                    correct = s.get("correct_answer", "")
                    if not sentence_text or not correct:
                        continue
                    sentence_obj = PracticeSentence(
                        word_id=word_id,
                        part_of_speech=pos_enum,
                        sentence=sentence_text,
                        correct_answer=correct,
                        case=s.get("case"),
                        gender=s.get("gender"),
                        number=s.get("number"),
                        pronoun=s.get("pronoun"),
                        tense=s.get("tense"),
                    )
                    session.add(sentence_obj)
                session.commit()

    except Exception as e:
        print(f"Background form generation error for word {word_id}: {e}")


@router.get("/initial", response_model=list[WordRead])
def get_initial_words(count: int = 10) -> list[WordRead]:
    with Session(engine) as session:
        return session.exec(select(Word).limit(count)).all()


@router.put("/{word_id}", response_model=WordRead)
def update_word(word_id: int, payload: WordUpdateRequest) -> WordRead:
    polish = payload.polish.strip()
    english = payload.english.strip()
    ukrainian = payload.ukrainian.strip()
    if not polish or not english or not ukrainian:
        raise HTTPException(status_code=400, detail="All translation fields are required")

    with Session(engine) as session:
        word = session.get(Word, word_id)
        if not word:
            raise HTTPException(status_code=404, detail="Word not found")
        word.polish = polish
        word.english = english
        word.ukrainian = ukrainian
        session.add(word)
        session.commit()
        session.refresh(word)
        return WordRead.model_validate(word)


@router.post("/check", response_model=WordCheckResponse)
def check_word(payload: WordCheckRequest) -> WordCheckResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Value is required")

    normalized = text.lower().strip()
    with Session(engine) as session:
        for field in ("polish", "english", "ukrainian"):
            statement = select(Word).where(
                func.lower(getattr(Word, field)) == normalized
            )
            word = session.exec(statement).first()
            if word:
                return WordCheckResponse(
                    found=True,
                    word=WordRead.model_validate(word),
                    matched_field=field,
                    created=False,
                    source="database",
                )

        try:
            resolved = resolve_word_via_llm(text)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        required_fields = ("polish", "english", "ukrainian")
        if not all(resolved.get(field) for field in required_fields):
            raise HTTPException(
                status_code=422, detail="Unable to resolve translations"
            )

        resolved_normalized = {
            field: resolved[field].lower().strip() for field in required_fields
        }
        for field, normalized_value in resolved_normalized.items():
            statement = select(Word).where(
                func.lower(getattr(Word, field)) == normalized_value
            )
            word = session.exec(statement).first()
            if word:
                # Update part_of_speech if it was "inne" and LLM gave something better
                pos = resolved.get("part_of_speech", "inne")
                if word.part_of_speech == PartOfSpeech.inne and pos != "inne":
                    try:
                        word.part_of_speech = PartOfSpeech(pos)
                        if resolved.get("gender"):
                            word.gender = resolved["gender"]
                        session.add(word)
                        session.commit()
                        session.refresh(word)
                    except ValueError:
                        pass
                return WordCheckResponse(
                    found=True,
                    word=WordRead.model_validate(word),
                    matched_field=field,
                    created=False,
                    source="database",
                )

        pos = resolved.get("part_of_speech", "inne")
        try:
            pos_enum = PartOfSpeech(pos)
        except ValueError:
            pos_enum = PartOfSpeech.inne

        new_word = Word(
            polish=resolved["polish"],
            english=resolved["english"],
            ukrainian=resolved["ukrainian"],
            part_of_speech=pos_enum,
            gender=resolved.get("gender"),
        )
        session.add(new_word)
        session.commit()
        session.refresh(new_word)

        # Generate forms in background
        if pos_enum in (PartOfSpeech.rzeczownik, PartOfSpeech.przymiotnik, PartOfSpeech.czasownik):
            threading.Thread(
                target=_generate_forms_background,
                args=(new_word.id, new_word.polish, pos_enum.value, new_word.gender),
                daemon=True,
            ).start()

        return WordCheckResponse(
            found=True,
            word=WordRead.model_validate(new_word),
            matched_field="resolved",
            created=True,
            source="llm",
        )


def get_or_create_session(session: Session) -> UserSession:
    state = session.exec(select(UserSession)).first()
    if not state:
        state = UserSession()
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


def check_single_word(
    session: Session, text: str, session_word_ids: set[int]
) -> WordCheckResult:
    normalized = text.lower().strip()

    for field in ("polish", "english", "ukrainian"):
        statement = select(Word).where(func.lower(getattr(Word, field)) == normalized)
        word = session.exec(statement).first()
        if word:
            is_duplicate = word.id in session_word_ids
            return WordCheckResult(
                text=text,
                found=True,
                word=WordRead.model_validate(word),
                matched_field=field,
                created=False,
                source="database",
                duplicate=is_duplicate,
            )

    try:
        resolved = resolve_word_via_llm(text)
    except RuntimeError:
        return WordCheckResult(text=text, found=False, source="llm_error")

    required_fields = ("polish", "english", "ukrainian")
    if not all(resolved.get(field) for field in required_fields):
        return WordCheckResult(text=text, found=False, source="llm_incomplete")

    resolved_normalized = {
        field: resolved[field].lower().strip() for field in required_fields
    }
    for field, normalized_value in resolved_normalized.items():
        statement = select(Word).where(
            func.lower(getattr(Word, field)) == normalized_value
        )
        word = session.exec(statement).first()
        if word:
            is_duplicate = word.id in session_word_ids
            return WordCheckResult(
                text=text,
                found=True,
                word=WordRead.model_validate(word),
                matched_field=field,
                created=False,
                source="database",
                duplicate=is_duplicate,
            )

    pos = resolved.get("part_of_speech", "inne")
    try:
        pos_enum = PartOfSpeech(pos)
    except ValueError:
        pos_enum = PartOfSpeech.inne

    new_word = Word(
        polish=resolved["polish"],
        english=resolved["english"],
        ukrainian=resolved["ukrainian"],
        part_of_speech=pos_enum,
        gender=resolved.get("gender"),
    )
    session.add(new_word)
    session.commit()
    session.refresh(new_word)

    # Generate forms in background
    if pos_enum in (PartOfSpeech.rzeczownik, PartOfSpeech.przymiotnik, PartOfSpeech.czasownik):
        threading.Thread(
            target=_generate_forms_background,
            args=(new_word.id, new_word.polish, pos_enum.value, new_word.gender),
            daemon=True,
        ).start()

    return WordCheckResult(
        text=text,
        found=True,
        word=WordRead.model_validate(new_word),
        matched_field="resolved",
        created=True,
        source="llm",
        duplicate=False,
    )


@router.post("/check/bulk", response_model=WordCheckBulkResponse)
def check_words_bulk(payload: WordCheckBulkRequest) -> WordCheckBulkResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Value is required")

    words_to_check = [w.strip() for w in text.split(",") if w.strip()]
    if not words_to_check:
        raise HTTPException(status_code=400, detail="No valid words found")

    results: list[WordCheckResult] = []
    added_count = 0
    duplicate_count = 0
    failed_count = 0

    with Session(engine) as session:
        user_session = get_or_create_session(session)
        existing_session_words = session.exec(
            select(UserSessionWord.word_id).where(
                UserSessionWord.session_id == user_session.id
            )
        ).all()
        session_word_ids = set(existing_session_words)

        for word_text in words_to_check:
            result = check_single_word(session, word_text, session_word_ids)
            results.append(result)

            if result.found and result.word:
                if result.duplicate:
                    duplicate_count += 1
                else:
                    session.add(
                        UserSessionWord(
                            session_id=user_session.id,
                            word_id=result.word.id,
                        )
                    )
                    session_word_ids.add(result.word.id)
                    added_count += 1
            else:
                failed_count += 1

        session.commit()

    return WordCheckBulkResponse(
        results=results,
        added_count=added_count,
        duplicate_count=duplicate_count,
        failed_count=failed_count,
    )
