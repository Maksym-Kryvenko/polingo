from datetime import datetime, timedelta

from fastapi import APIRouter
from sqlmodel import Session, select

from app.database import engine
from app.models import ConnectedDevice
from app.schemas import DeviceRead, DevicesResponse

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
