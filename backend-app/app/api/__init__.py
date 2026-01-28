from fastapi import APIRouter

from app.api.practice import router as practice_router
from app.api.session import router as session_router
from app.api.stats import router as stats_router
from app.api.words import router as words_router
from app.api.verbs import router as verbs_router

router = APIRouter()
router.include_router(words_router)
router.include_router(practice_router)
router.include_router(stats_router)
router.include_router(session_router)
router.include_router(verbs_router)
