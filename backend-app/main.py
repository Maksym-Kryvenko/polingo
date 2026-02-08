import hashlib
from datetime import datetime
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlmodel import Session, select

from app.api import router as api_router
from app.database import engine, init_db
from app.models import ConnectedDevice

app = FastAPI(
    title="Polingo API",
    version="0.1.0",
    description="API for a beginner-friendly Polish vocabulary trainer",
)

load_dotenv()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_user_agent(user_agent: str) -> dict:
    """Parse user agent string to extract device info."""
    ua_lower = user_agent.lower()

    # Detect device type
    if any(x in ua_lower for x in ["mobile", "android", "iphone", "ipod"]):
        device_type = "mobile"
    elif any(x in ua_lower for x in ["ipad", "tablet"]):
        device_type = "tablet"
    elif any(x in ua_lower for x in ["windows", "macintosh", "linux", "x11"]):
        device_type = "desktop"
    else:
        device_type = "unknown"

    # Detect browser
    if "firefox" in ua_lower:
        browser = "Firefox"
    elif "edg" in ua_lower:
        browser = "Edge"
    elif "chrome" in ua_lower or "crios" in ua_lower:
        browser = "Chrome"
    elif "safari" in ua_lower:
        browser = "Safari"
    elif "opera" in ua_lower or "opr" in ua_lower:
        browser = "Opera"
    else:
        browser = "Unknown"

    # Detect OS
    if "windows" in ua_lower:
        os = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        os = "macOS"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os = "iOS"
    elif "android" in ua_lower:
        os = "Android"
    elif "linux" in ua_lower:
        os = "Linux"
    else:
        os = "Unknown"

    return {"device_type": device_type, "browser": browser, "os": os}


def get_device_fingerprint(ip_address: str, user_agent: str) -> str:
    """Create a unique fingerprint for a device based on IP + user agent."""
    raw = f"{ip_address}|{user_agent}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@app.middleware("http")
async def track_devices(request: Request, call_next):
    """Middleware to track connected devices."""
    response = await call_next(request)

    # Skip tracking for admin endpoints to avoid self-tracking during polling
    if "/admin/" in request.url.path:
        return response

    # Get client IP (handle proxy headers)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown"

    user_agent = request.headers.get("user-agent", "Unknown")
    device_info = parse_user_agent(user_agent)

    # Create unique fingerprint from IP + user agent
    fingerprint = get_device_fingerprint(ip_address, user_agent)

    try:
        with Session(engine) as session:
            # Find existing device by fingerprint (IP + user agent combo)
            existing = session.exec(
                select(ConnectedDevice).where(
                    ConnectedDevice.ip_address == ip_address,
                    ConnectedDevice.device_type == device_info["device_type"],
                    ConnectedDevice.browser == device_info["browser"],
                    ConnectedDevice.os == device_info["os"],
                )
            ).first()

            if existing:
                existing.last_activity = datetime.utcnow()
                existing.request_count += 1
            else:
                new_device = ConnectedDevice(
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device_type=device_info["device_type"],
                    browser=device_info["browser"],
                    os=device_info["os"],
                )
                session.add(new_device)

            session.commit()
    except Exception as e:
        # Don't let tracking errors break the app
        print(f"Device tracking error: {e}")

    return response


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
