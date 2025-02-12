from datetime import datetime, timedelta
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseSettings
from statistics import median


class Settings(BaseSettings):
    mongodb_url: str
    mongodb_db_name: str

    class Config:
        env_file = ".env"
        env_prefix = ""


settings = Settings()
client = AsyncIOMotorClient(settings.mongodb_url)
db = client[settings.mongodb_db_name]
heartbeats = db["heartbeats"]


async def store_heartbeat(service_key: str, timestamp: datetime, metadata: Optional[dict] = None) -> None:
    """Store a heartbeat in the database"""
    await heartbeats.insert_one({
        "service_key": service_key,
        "timestamp": timestamp,
        "metadata": metadata or {}
    })


async def get_service_status(service_key: str) -> dict:
    """Get the status of a service including its state and median heartbeat interval"""
    # Get all heartbeats for this service, ordered by timestamp
    service_heartbeats = await heartbeats.find(
        {"service_key": service_key}
    ).sort("timestamp", -1).to_list(None)

    if not service_heartbeats:
        return None

    last_heartbeat = service_heartbeats[0]["timestamp"]
    now = datetime.utcnow()
    time_since_last = (now - last_heartbeat).total_seconds()

    # Calculate state
    if time_since_last > 24 * 3600:  # More than 24 hours
        state = "dead"
    elif time_since_last > 3600:  # More than 1 hour
        state = "down"
    else:
        state = "ok"

    # Calculate median interval
    intervals = []
    for i in range(1, len(service_heartbeats)):
        interval = (service_heartbeats[i-1]["timestamp"] - 
                   service_heartbeats[i]["timestamp"]).total_seconds()
        # Filter out intervals longer than 1 hour to avoid skewing the median
        if interval < 3600:
            intervals.append(interval)

    median_interval = median(intervals) if intervals else 0

    return {
        "service_key": service_key,
        "last_heartbeat": last_heartbeat,
        "state": state,
        "median_interval": median_interval,
        "metadata": service_heartbeats[0].get("metadata", {})
    }


async def get_all_services() -> List[str]:
    """Get a list of all service keys"""
    return await heartbeats.distinct("service_key") 