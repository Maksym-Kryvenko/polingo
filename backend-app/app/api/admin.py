from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models import ConnectedDevice, AppSetting, PracticeSentence, Word
from app.schemas import (
    DeviceRead, DevicesResponse, AppSettingRead, AppSettingUpdate,
    PracticeSentenceRead, PracticeSentenceUpdate, SentenceFixRequest,
)
from app.llm import fix_sentence_via_llm

router = APIRouter(prefix="/admin", tags=["admin"])

# Device is considered active if last activity was within this time
ACTIVE_THRESHOLD_MINUTES = 5


@router.get("/devices", response_model=DevicesResponse)
def get_connected_devices() -> DevicesResponse:
    """Get all connected devices with their status."""
    with Session(engine) as session:
        devices = session.exec(
            select(ConnectedDevice).order_by(ConnectedDevice.last_activity.desc())
        ).all()

        now = datetime.utcnow()
        threshold = now - timedelta(minutes=ACTIVE_THRESHOLD_MINUTES)

        device_list = []
        active_count = 0

        for device in devices:
            is_active = device.last_activity >= threshold
            if is_active:
                active_count += 1

            device_list.append(
                DeviceRead(
                    id=device.id,
                    ip_address=device.ip_address,
                    user_agent=device.user_agent,
                    device_type=device.device_type,
                    browser=device.browser,
                    os=device.os,
                    first_seen=device.first_seen,
                    last_activity=device.last_activity,
                    request_count=device.request_count,
                    is_active=is_active,
                )
            )

        return DevicesResponse(
            devices=device_list,
            total_count=len(device_list),
            active_count=active_count,
        )


@router.delete("/devices/{device_id}")
def delete_device(device_id: int) -> dict:
    """Delete a device from tracking."""
    with Session(engine) as session:
        device = session.get(ConnectedDevice, device_id)
        if device:
            session.delete(device)
            session.commit()
            return {"success": True, "message": "Device removed"}
        return {"success": False, "message": "Device not found"}


@router.delete("/devices")
def clear_all_devices() -> dict:
    """Clear all device tracking data."""
    with Session(engine) as session:
        devices = session.exec(select(ConnectedDevice)).all()
        for device in devices:
            session.delete(device)
        session.commit()
        return {"success": True, "message": f"Removed {len(devices)} devices"}


@router.get("/settings", response_model=list[AppSettingRead])
def get_settings() -> list[AppSettingRead]:
    with Session(engine) as session:
        settings = session.exec(select(AppSetting)).all()
        return [AppSettingRead(key=s.key, value=s.value) for s in settings]


@router.get("/settings/{key}", response_model=AppSettingRead)
def get_setting(key: str) -> AppSettingRead:
    with Session(engine) as session:
        setting = session.get(AppSetting, key)
        if not setting:
            raise HTTPException(status_code=404, detail="Setting not found")
        return AppSettingRead(key=setting.key, value=setting.value)


@router.put("/settings/{key}", response_model=AppSettingRead)
def update_setting(key: str, payload: AppSettingUpdate) -> AppSettingRead:
    with Session(engine) as session:
        setting = session.get(AppSetting, key)
        if not setting:
            setting = AppSetting(key=key, value=payload.value)
            session.add(setting)
        else:
            setting.value = payload.value
            session.add(setting)
        session.commit()
        session.refresh(setting)
        return AppSettingRead(key=setting.key, value=setting.value)


# ── Sentence management ──────────────────────────────────────


@router.get("/sentences", response_model=list[PracticeSentenceRead])
def get_sentences() -> list[PracticeSentenceRead]:
    """List all practice sentences with word info."""
    with Session(engine) as session:
        sentences = session.exec(
            select(PracticeSentence).order_by(PracticeSentence.id.desc())
        ).all()
        result = []
        for s in sentences:
            word = session.get(Word, s.word_id)
            result.append(PracticeSentenceRead(
                id=s.id,
                word_id=s.word_id,
                word_polish=word.polish if word else "?",
                part_of_speech=s.part_of_speech.value if hasattr(s.part_of_speech, 'value') else str(s.part_of_speech),
                sentence=s.sentence,
                correct_answer=s.correct_answer,
                case=s.case,
                gender=s.gender,
                number=s.number,
                pronoun=s.pronoun,
                tense=s.tense,
            ))
        return result


@router.put("/sentences/{sentence_id}", response_model=PracticeSentenceRead)
def update_sentence(sentence_id: int, payload: PracticeSentenceUpdate) -> PracticeSentenceRead:
    """Manually edit a sentence."""
    with Session(engine) as session:
        s = session.get(PracticeSentence, sentence_id)
        if not s:
            raise HTTPException(status_code=404, detail="Sentence not found")
        if payload.sentence is not None:
            s.sentence = payload.sentence
        if payload.correct_answer is not None:
            s.correct_answer = payload.correct_answer
        session.add(s)
        session.commit()
        session.refresh(s)
        word = session.get(Word, s.word_id)
        return PracticeSentenceRead(
            id=s.id,
            word_id=s.word_id,
            word_polish=word.polish if word else "?",
            part_of_speech=s.part_of_speech.value if hasattr(s.part_of_speech, 'value') else str(s.part_of_speech),
            sentence=s.sentence,
            correct_answer=s.correct_answer,
            case=s.case, gender=s.gender, number=s.number,
            pronoun=s.pronoun, tense=s.tense,
        )


@router.post("/sentences/{sentence_id}/fix", response_model=PracticeSentenceRead)
def fix_sentence_with_llm(sentence_id: int) -> PracticeSentenceRead:
    """Ask LLM to fix a sentence."""
    with Session(engine) as session:
        s = session.get(PracticeSentence, sentence_id)
        if not s:
            raise HTTPException(status_code=404, detail="Sentence not found")
        word = session.get(Word, s.word_id)
        pos = s.part_of_speech.value if hasattr(s.part_of_speech, 'value') else str(s.part_of_speech)
        fixed = fix_sentence_via_llm(
            sentence=s.sentence,
            correct_answer=s.correct_answer,
            polish_word=word.polish if word else "",
            part_of_speech=pos,
        )
        if fixed.get("sentence"):
            s.sentence = fixed["sentence"]
        if fixed.get("correct_answer"):
            s.correct_answer = fixed["correct_answer"]
        session.add(s)
        session.commit()
        session.refresh(s)
        return PracticeSentenceRead(
            id=s.id,
            word_id=s.word_id,
            word_polish=word.polish if word else "?",
            part_of_speech=pos,
            sentence=s.sentence,
            correct_answer=s.correct_answer,
            case=s.case, gender=s.gender, number=s.number,
            pronoun=s.pronoun, tense=s.tense,
        )


@router.delete("/sentences/{sentence_id}")
def delete_sentence(sentence_id: int) -> dict:
    """Delete a practice sentence."""
    with Session(engine) as session:
        s = session.get(PracticeSentence, sentence_id)
        if not s:
            return {"success": False, "message": "Sentence not found"}
        session.delete(s)
        session.commit()
        return {"success": True, "message": "Sentence deleted"}
