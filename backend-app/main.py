from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api import router as api_router
from app.database import init_db

app = FastAPI(
    title="Polingo API",
    version="0.1.0",
    description="API for a beginner-friendly Polish vocabulary trainer",
)

load_dotenv()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/healthz")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "polingo"}


app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
