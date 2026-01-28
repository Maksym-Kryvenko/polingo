import random
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select, func

from app.database import engine
from app.llm import generate_verb_conjugations_via_llm
from app.models import (
    Pronoun,
    UserSession,
    UserSessionVerb,
    Verb,
    VerbConjugation,
    VerbPracticeRecord,
)
from app.schemas import (
    EndingsQuestion,
    EndingsStatsResponse,
    EndingsValidationRequest,
    EndingsValidationResponse,
    VerbAddRequest,
    VerbAddResponse,
    VerbConjugationRead,
    VerbSessionState,
    VerbWithConjugations,
)

router = APIRouter(prefix="/verbs", tags=["verbs"])

PRONOUN_MAP = {
    "ja": Pronoun.ja,
    "ty": Pronoun.ty,
    "on_ona_ono": Pronoun.on_ona_ono,
    "my": Pronoun.my,
    "wy": Pronoun.wy,
    "oni_one": Pronoun.oni_one,
}


def get_verb_with_conjugations_and_stats(
    session: Session, verb: Verb
) -> VerbWithConjugations:
    """Get a verb with its conjugations and practice stats."""
    conjugations = session.exec(
        select(VerbConjugation).where(VerbConjugation.verb_id == verb.id)
    ).all()

    # Calculate stats for this verb
    total = session.exec(
        select(func.count(VerbPracticeRecord.id)).where(
            VerbPracticeRecord.verb_id == verb.id
        )
    ).one()
    correct = session.exec(
        select(func.count(VerbPracticeRecord.id)).where(
            VerbPracticeRecord.verb_id == verb.id,
            VerbPracticeRecord.was_correct == True,
        )
    ).one()

    error_rate = round((1 - correct / total) * 100, 1) if total > 0 else 0.0

    return VerbWithConjugations(
        id=verb.id,
        infinitive=verb.infinitive,
        english=verb.english,
        ukrainian=verb.ukrainian,
        conjugations=[
            VerbConjugationRead(
                pronoun=c.pronoun.value, conjugated_form=c.conjugated_form
            )
            for c in conjugations
        ],
        total_attempts=total,
        correct_attempts=correct,
        error_rate=error_rate,
    )


def calculate_endings_stats(session: Session) -> EndingsStatsResponse:
    """Calculate stats specifically for verb/endings practice."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Today's stats
    today_total = session.exec(
        select(func.count(VerbPracticeRecord.id)).where(
            VerbPracticeRecord.practice_date == today
        )
    ).one()
    today_correct = session.exec(
        select(func.count(VerbPracticeRecord.id)).where(
            VerbPracticeRecord.practice_date == today,
            VerbPracticeRecord.was_correct == True,
        )
    ).one()
    today_percentage = (
        round(today_correct / today_total * 100, 1) if today_total > 0 else 0.0
    )

    # Yesterday's stats for trend
    yesterday_total = session.exec(
        select(func.count(VerbPracticeRecord.id)).where(
            VerbPracticeRecord.practice_date == yesterday
        )
    ).one()
    yesterday_correct = session.exec(
        select(func.count(VerbPracticeRecord.id)).where(
            VerbPracticeRecord.practice_date == yesterday,
            VerbPracticeRecord.was_correct == True,
        )
    ).one()
    yesterday_percentage = (
        round(yesterday_correct / yesterday_total * 100, 1)
        if yesterday_total > 0
        else 0.0
    )
    trend = round(today_percentage - yesterday_percentage, 1)

    # Overall stats
    overall_total = session.exec(select(func.count(VerbPracticeRecord.id))).one()
    overall_correct = session.exec(
        select(func.count(VerbPracticeRecord.id)).where(
            VerbPracticeRecord.was_correct == True
        )
    ).one()
    overall_percentage = (
        round(overall_correct / overall_total * 100, 1) if overall_total > 0 else 0.0
    )

    # Available verbs count
    available_verbs = session.exec(select(func.count(Verb.id))).one()

    return EndingsStatsResponse(
        today_percentage=today_percentage,
        trend=trend,
        overall_percentage=overall_percentage,
        available_verbs=available_verbs,
    )


@router.post("/add", response_model=VerbAddResponse)
def add_verb(payload: VerbAddRequest) -> VerbAddResponse:
    """Add a new verb by providing English or Ukrainian translation."""
    with Session(engine) as session:
        # Check if verb already exists (by checking infinitive after LLM call)
        try:
            llm_result = generate_verb_conjugations_via_llm(
                payload.text, payload.source_language
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"LLM generation failed: {str(exc)}"
            ) from exc

        if not llm_result.get("infinitive"):
            return VerbAddResponse(
                success=False,
                message="Could not generate conjugations. Please check the input.",
                duplicate=False,
            )

        # Check for existing verb
        existing = session.exec(
            select(Verb).where(Verb.infinitive == llm_result["infinitive"])
        ).first()

        if existing:
            verb_with_conj = get_verb_with_conjugations_and_stats(session, existing)
            return VerbAddResponse(
                success=True,
                verb=verb_with_conj,
                message=f"Verb '{existing.infinitive}' already exists.",
                duplicate=True,
            )

        # Create new verb
        verb = Verb(
            infinitive=llm_result["infinitive"],
            english=llm_result["english"],
            ukrainian=llm_result["ukrainian"],
        )
        session.add(verb)
        session.flush()

        # Add conjugations
        conjugations_data = llm_result.get("conjugations", {})
        for pronoun_key, conjugated_form in conjugations_data.items():
            if pronoun_key in PRONOUN_MAP and conjugated_form:
                conj = VerbConjugation(
                    verb_id=verb.id,
                    pronoun=PRONOUN_MAP[pronoun_key],
                    conjugated_form=conjugated_form,
                )
                session.add(conj)

        session.commit()
        session.refresh(verb)

        verb_with_conj = get_verb_with_conjugations_and_stats(session, verb)
        return VerbAddResponse(
            success=True,
            verb=verb_with_conj,
            message=f"Added verb '{verb.infinitive}' with all conjugations.",
            duplicate=False,
        )


@router.get("/session", response_model=VerbSessionState)
def get_verb_session() -> VerbSessionState:
    """Get all verbs in the user's session."""
    with Session(engine) as session:
        user_session = session.exec(select(UserSession)).first()
        if not user_session:
            return VerbSessionState(verbs=[])

        session_verbs = session.exec(
            select(UserSessionVerb).where(UserSessionVerb.session_id == user_session.id)
        ).all()

        verbs = []
        for sv in session_verbs:
            verb = session.get(Verb, sv.verb_id)
            if verb:
                verbs.append(get_verb_with_conjugations_and_stats(session, verb))

        # Sort by error rate descending (most errors first)
        verbs.sort(key=lambda v: (-v.error_rate, -v.total_attempts))

        return VerbSessionState(verbs=verbs)


@router.post("/session", response_model=VerbSessionState)
def add_verb_to_session(verb_id: int) -> VerbSessionState:
    """Add a verb to the user's session."""
    with Session(engine) as session:
        user_session = session.exec(select(UserSession)).first()
        if not user_session:
            user_session = UserSession()
            session.add(user_session)
            session.flush()

        verb = session.get(Verb, verb_id)
        if not verb:
            raise HTTPException(status_code=404, detail="Verb not found")

        # Check if already in session
        existing = session.exec(
            select(UserSessionVerb).where(
                UserSessionVerb.session_id == user_session.id,
                UserSessionVerb.verb_id == verb_id,
            )
        ).first()

        if not existing:
            session.add(UserSessionVerb(session_id=user_session.id, verb_id=verb_id))
            session.commit()

        return get_verb_session()


@router.get("/question", response_model=EndingsQuestion)
def get_endings_question() -> EndingsQuestion:
    """Get a random conjugation question from session verbs."""
    with Session(engine) as session:
        user_session = session.exec(select(UserSession)).first()
        if not user_session:
            raise HTTPException(status_code=400, detail="No session found")

        session_verbs = session.exec(
            select(UserSessionVerb).where(UserSessionVerb.session_id == user_session.id)
        ).all()

        if not session_verbs:
            raise HTTPException(
                status_code=400, detail="No verbs in session. Add some verbs first."
            )

        # Pick a random verb
        random_sv = random.choice(session_verbs)
        verb = session.get(Verb, random_sv.verb_id)
        if not verb:
            raise HTTPException(status_code=404, detail="Verb not found")

        # Get all conjugations for this verb
        conjugations = session.exec(
            select(VerbConjugation).where(VerbConjugation.verb_id == verb.id)
        ).all()

        if not conjugations:
            raise HTTPException(status_code=400, detail="Verb has no conjugations")

        # Pick a random conjugation as the question
        target_conj = random.choice(conjugations)

        # Create options: correct + 3 wrong (other conjugations)
        other_conjs = [c for c in conjugations if c.id != target_conj.id]
        wrong_options = random.sample(
            [c.conjugated_form for c in other_conjs],
            min(3, len(other_conjs)),
        )

        # If we don't have enough wrong options, pad with variations
        while len(wrong_options) < 3:
            wrong_options.append(f"{target_conj.conjugated_form}?")

        options = [target_conj.conjugated_form] + wrong_options
        random.shuffle(options)

        return EndingsQuestion(
            verb_id=verb.id,
            infinitive=verb.infinitive,
            english=verb.english,
            ukrainian=verb.ukrainian,
            pronoun=target_conj.pronoun.value,
            correct_answer=target_conj.conjugated_form,
            options=options,
        )


@router.post("/validate", response_model=EndingsValidationResponse)
def validate_endings(payload: EndingsValidationRequest) -> EndingsValidationResponse:
    """Validate an endings practice answer."""
    with Session(engine) as session:
        verb = session.get(Verb, payload.verb_id)
        if not verb:
            raise HTTPException(status_code=404, detail="Verb not found")

        # Find the correct conjugation
        pronoun_enum = None
        for key, val in PRONOUN_MAP.items():
            if val.value == payload.pronoun:
                pronoun_enum = val
                break

        if not pronoun_enum:
            raise HTTPException(status_code=400, detail="Invalid pronoun")

        conjugation = session.exec(
            select(VerbConjugation).where(
                VerbConjugation.verb_id == verb.id,
                VerbConjugation.pronoun == pronoun_enum,
            )
        ).first()

        if not conjugation:
            raise HTTPException(status_code=404, detail="Conjugation not found")

        is_correct = (
            payload.answer.strip().lower() == conjugation.conjugated_form.lower()
        )

        # Record the practice
        session.add(
            VerbPracticeRecord(
                verb_id=verb.id,
                pronoun=pronoun_enum,
                was_correct=is_correct,
            )
        )
        session.commit()

        return EndingsValidationResponse(
            was_correct=is_correct,
            correct_answer=conjugation.conjugated_form,
            stats=calculate_endings_stats(session),
        )


@router.get("/stats", response_model=EndingsStatsResponse)
def get_endings_stats() -> EndingsStatsResponse:
    """Get endings practice statistics."""
    with Session(engine) as session:
        return calculate_endings_stats(session)
