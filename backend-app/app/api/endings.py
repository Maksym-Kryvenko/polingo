import random
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select, func

from app.database import engine
from app.grammar import get_grammar_reference
from app.llm import generate_sentence_on_the_fly
from app.models import (
    AppSetting,
    EndingsPracticeRecord,
    GrammaticalCase,
    GrammaticalGender,
    GrammaticalNumber,
    PartOfSpeech,
    PracticeSentence,
    Pronoun,
    VerbConjugation,
    VerbTense,
    Word,
    WordDeclension,
)
from app.schemas import (
    EndingsConfigResponse,
    EndingsQuestion,
    EndingsStatsResponse,
    EndingsValidationRequest,
    EndingsValidationResponse,
)

router = APIRouter(prefix="/endings", tags=["endings"])


@router.get("/config", response_model=EndingsConfigResponse)
def get_endings_config() -> EndingsConfigResponse:
    return EndingsConfigResponse(
        parts_of_speech=[p.value for p in [PartOfSpeech.rzeczownik, PartOfSpeech.przymiotnik, PartOfSpeech.czasownik]],
        cases=[c.value for c in GrammaticalCase],
        tenses=[t.value for t in VerbTense],
    )


def _get_noun_adj_question(
    session: Session,
    pos_value: str,
    cases: list[str],
    use_on_the_fly: bool,
    exclude_word_id: int | None = None,
) -> EndingsQuestion | None:
    """Build a question for rzeczownik or przymiotnik."""
    pos_enum = PartOfSpeech(pos_value)

    # Get words that have declension data
    word_ids_with_forms = session.exec(
        select(WordDeclension.word_id).distinct()
        .join(Word, Word.id == WordDeclension.word_id)
        .where(Word.part_of_speech == pos_enum)
    ).all()
    if not word_ids_with_forms:
        return None

    # Avoid repeating the same word if possible
    candidates = [wid for wid in word_ids_with_forms if wid != exclude_word_id]
    if not candidates:
        candidates = word_ids_with_forms
    word_id = random.choice(candidates)
    word = session.get(Word, word_id)
    if not word:
        return None

    # Pick a random case from the requested ones
    case_str = random.choice(cases)

    # Try pre-generated sentence first
    if not use_on_the_fly:
        sentences = session.exec(
            select(PracticeSentence).where(
                PracticeSentence.word_id == word_id,
                PracticeSentence.part_of_speech == pos_enum,
                PracticeSentence.case == case_str,
            )
        ).all()
        sentence = random.choice(sentences) if sentences else None
        if sentence:
            correct = sentence.correct_answer
            options = _build_options(session, word_id, correct, pos_value, case_str=case_str)
            grammar = get_grammar_reference(pos_value, case=case_str)
            return EndingsQuestion(
                word_id=word.id,
                polish=word.polish,
                english=word.english,
                ukrainian=word.ukrainian,
                part_of_speech=pos_value,
                sentence=sentence.sentence,
                correct_answer=correct,
                options=options,
                case=case_str,
                gender=sentence.gender or word.gender,
                number=sentence.number or "singular",
                grammar_reference=grammar,
            )

    # Fall back to on-the-fly generation or random declension
    declension = session.exec(
        select(WordDeclension).where(
            WordDeclension.word_id == word_id,
            WordDeclension.case == GrammaticalCase(case_str),
        )
    ).first()
    if not declension:
        return None

    if use_on_the_fly:
        result = generate_sentence_on_the_fly(
            word.polish, pos_value,
            case=case_str, gender=declension.gender.value, number=declension.number.value,
        )
        sentence_text = result.get("sentence", f"Użyj formy ___ ({case_str})")
        correct = result.get("correct_answer", declension.form)
        wrong = result.get("wrong_options", [])
        all_options = [correct] + [w for w in wrong if w != correct]
        random.shuffle(all_options)
        options = all_options[:4]
        # Persist generated sentence for future reuse
        if sentence_text and correct:
            session.add(PracticeSentence(
                word_id=word_id, part_of_speech=pos_enum,
                sentence=sentence_text, correct_answer=correct,
                case=case_str, gender=declension.gender.value,
                number=declension.number.value,
            ))
            session.commit()
    else:
        sentence_text = f"({case_str}) ___"
        correct = declension.form
        options = _build_options(session, word_id, correct, pos_value, case_str=case_str)

    grammar = get_grammar_reference(pos_value, case=case_str)
    return EndingsQuestion(
        word_id=word.id,
        polish=word.polish,
        english=word.english,
        ukrainian=word.ukrainian,
        part_of_speech=pos_value,
        sentence=sentence_text,
        correct_answer=correct,
        options=options,
        case=case_str,
        gender=declension.gender.value,
        number=declension.number.value,
        grammar_reference=grammar,
    )


def _get_verb_question(
    session: Session,
    tenses: list[str],
    use_on_the_fly: bool,
    exclude_word_id: int | None = None,
) -> EndingsQuestion | None:
    """Build a question for czasownik."""
    pos_enum = PartOfSpeech.czasownik

    word_ids_with_forms = session.exec(
        select(VerbConjugation.word_id).distinct()
        .join(Word, Word.id == VerbConjugation.word_id)
        .where(Word.part_of_speech == pos_enum)
    ).all()
    if not word_ids_with_forms:
        return None

    # Avoid repeating the same word if possible
    candidates = [wid for wid in word_ids_with_forms if wid != exclude_word_id]
    if not candidates:
        candidates = word_ids_with_forms
    word_id = random.choice(candidates)
    word = session.get(Word, word_id)
    if not word:
        return None

    tense_str = random.choice(tenses)

    if not use_on_the_fly:
        sentences = session.exec(
            select(PracticeSentence).where(
                PracticeSentence.word_id == word_id,
                PracticeSentence.part_of_speech == pos_enum,
                PracticeSentence.tense == tense_str,
            )
        ).all()
        sentence = random.choice(sentences) if sentences else None
        if sentence:
            correct = sentence.correct_answer
            options = _build_options(session, word_id, correct, "czasownik", tense_str=tense_str)
            grammar = get_grammar_reference("czasownik", tense=tense_str)
            return EndingsQuestion(
                word_id=word.id,
                polish=word.polish,
                english=word.english,
                ukrainian=word.ukrainian,
                part_of_speech="czasownik",
                sentence=sentence.sentence,
                correct_answer=correct,
                options=options,
                pronoun=sentence.pronoun,
                tense=tense_str,
                grammar_reference=grammar,
            )

    conjugation = session.exec(
        select(VerbConjugation).where(
            VerbConjugation.word_id == word_id,
            VerbConjugation.tense == VerbTense(tense_str),
        )
    ).first()
    if not conjugation:
        return None

    if use_on_the_fly:
        result = generate_sentence_on_the_fly(
            word.polish, "czasownik",
            pronoun=conjugation.pronoun.value, tense=tense_str,
        )
        sentence_text = result.get("sentence", f"{conjugation.pronoun.value} ___")
        correct = result.get("correct_answer", conjugation.conjugated_form)
        wrong = result.get("wrong_options", [])
        all_options = [correct] + [w for w in wrong if w != correct]
        random.shuffle(all_options)
        options = all_options[:4]
        # Persist generated sentence for future reuse
        if sentence_text and correct:
            session.add(PracticeSentence(
                word_id=word_id, part_of_speech=pos_enum,
                sentence=sentence_text, correct_answer=correct,
                pronoun=conjugation.pronoun.value, tense=tense_str,
            ))
            session.commit()
    else:
        sentence_text = f"{conjugation.pronoun.value} ___"
        correct = conjugation.conjugated_form
        options = _build_options(session, word_id, correct, "czasownik", tense_str=tense_str)

    grammar = get_grammar_reference("czasownik", tense=tense_str)
    return EndingsQuestion(
        word_id=word.id,
        polish=word.polish,
        english=word.english,
        ukrainian=word.ukrainian,
        part_of_speech="czasownik",
        sentence=sentence_text,
        correct_answer=correct,
        options=options,
        pronoun=conjugation.pronoun.value,
        tense=tense_str,
        grammar_reference=grammar,
    )


def _build_options(
    session: Session,
    word_id: int,
    correct: str,
    pos_value: str,
    *,
    case_str: str | None = None,
    tense_str: str | None = None,
) -> list[str]:
    """Build 4 multiple-choice options (1 correct + 3 distractors)."""
    distractors: list[str] = []

    if pos_value in ("rzeczownik", "przymiotnik"):
        # Get other forms of same word as distractors
        other_forms = session.exec(
            select(WordDeclension.form).where(
                WordDeclension.word_id == word_id,
                WordDeclension.form != correct,
            )
        ).all()
        distractors = list(set(other_forms))
    else:
        other_forms = session.exec(
            select(VerbConjugation.conjugated_form).where(
                VerbConjugation.word_id == word_id,
                VerbConjugation.conjugated_form != correct,
            )
        ).all()
        distractors = list(set(other_forms))

    random.shuffle(distractors)
    distractors = distractors[:3]

    # Pad with slight modifications if we don't have enough
    while len(distractors) < 3:
        fake = correct + "y" if not correct.endswith("y") else correct[:-1] + "i"
        if fake not in distractors and fake != correct:
            distractors.append(fake)
        else:
            fake2 = correct + "a" if not correct.endswith("a") else correct[:-1] + "ą"
            if fake2 not in distractors and fake2 != correct:
                distractors.append(fake2)
            else:
                break

    options = [correct] + distractors[:3]
    random.shuffle(options)
    return options


@router.get("/question", response_model=EndingsQuestion)
def get_endings_question(
    part_of_speech: str,
    cases: str | None = None,
    tenses: str | None = None,
    exclude_word_id: int | None = None,
) -> EndingsQuestion:
    """Get an endings practice question.

    Query params:
        part_of_speech: rzeczownik | przymiotnik | czasownik
        cases: comma-separated list of cases (for nouns/adj)
        tenses: comma-separated list of tenses (for verbs)
    """
    with Session(engine) as session:
        # Check on-the-fly setting
        setting = session.exec(
            select(AppSetting).where(AppSetting.key == "generate_on_the_fly")
        ).first()
        use_on_the_fly = setting and setting.value == "true"

        if part_of_speech in ("rzeczownik", "przymiotnik"):
            case_list = [c.strip() for c in (cases or "biernik").split(",") if c.strip()]
            question = _get_noun_adj_question(session, part_of_speech, case_list, use_on_the_fly, exclude_word_id)
        elif part_of_speech == "czasownik":
            tense_list = [t.strip() for t in (tenses or "teraźniejszy").split(",") if t.strip()]
            question = _get_verb_question(session, tense_list, use_on_the_fly, exclude_word_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid part_of_speech")

        if not question:
            raise HTTPException(
                status_code=404,
                detail="No words available for this practice type. Add some words first!",
            )
        return question


@router.post("/validate", response_model=EndingsValidationResponse)
def validate_endings(payload: EndingsValidationRequest) -> EndingsValidationResponse:
    answer = payload.answer.strip().lower()
    correct = payload.correct_answer.strip().lower()
    was_correct = answer == correct

    with Session(engine) as session:
        word = session.get(Word, payload.word_id)
        if word:
            session.add(EndingsPracticeRecord(
                word_id=payload.word_id,
                part_of_speech=word.part_of_speech,
                was_correct=was_correct,
                user_answer=payload.answer,
                correct_answer=payload.correct_answer,
            ))
            session.commit()

        stats = _calculate_endings_stats(session)

    return EndingsValidationResponse(
        was_correct=was_correct,
        correct_answer=payload.correct_answer,
        stats=stats,
    )


@router.get("/stats", response_model=EndingsStatsResponse)
def get_endings_stats() -> EndingsStatsResponse:
    with Session(engine) as session:
        return _calculate_endings_stats(session)


def _calculate_endings_stats(session: Session) -> EndingsStatsResponse:
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Today's stats
    today_records = session.exec(
        select(EndingsPracticeRecord).where(EndingsPracticeRecord.practice_date == today)
    ).all()
    today_total = len(today_records)
    today_correct = sum(1 for r in today_records if r.was_correct)
    today_pct = (today_correct / today_total * 100) if today_total > 0 else 0.0

    # Yesterday for trend
    yesterday_records = session.exec(
        select(EndingsPracticeRecord).where(
            EndingsPracticeRecord.practice_date == yesterday
        )
    ).all()
    yesterday_total = len(yesterday_records)
    yesterday_correct = sum(1 for r in yesterday_records if r.was_correct)
    yesterday_pct = (yesterday_correct / yesterday_total * 100) if yesterday_total > 0 else 0.0
    trend = today_pct - yesterday_pct

    # Overall
    all_records = session.exec(select(EndingsPracticeRecord)).all()
    all_total = len(all_records)
    all_correct = sum(1 for r in all_records if r.was_correct)
    overall_pct = (all_correct / all_total * 100) if all_total > 0 else 0.0

    # Count available words for endings practice
    available_words = session.exec(
        select(func.count(Word.id)).where(
            Word.part_of_speech.in_([
                PartOfSpeech.rzeczownik,
                PartOfSpeech.przymiotnik,
                PartOfSpeech.czasownik,
            ])
        )
    ).one()

    return EndingsStatsResponse(
        today_percentage=round(today_pct, 1),
        trend=round(trend, 1),
        overall_percentage=round(overall_pct, 1),
        available_words=available_words,
    )
