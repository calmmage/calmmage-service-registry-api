from time import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import statistics
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings

from api.models import ServiceStatus, ServiceStatusResponse


def format_timedelta(td: timedelta) -> str:
    """Format timedelta into human readable string"""
    total_seconds = int(td.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    
    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    
    days, hours = divmod(hours, 24)
    if days < 7:
        return f"{days}d {hours}h"
    
    weeks, days = divmod(days, 7)
    return f"{weeks}w {days}d"


class Settings(BaseSettings):
    # MongoDB settings
    mongodb_url: str
    mongodb_db_name: str

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
client = AsyncIOMotorClient(settings.mongodb_url)
db = client[settings.mongodb_db_name]
heartbeats = db["heartbeats"]


async def store_heartbeat(service_key: str, metadata: Optional[dict] = None) -> None:
    """Store a heartbeat in the database"""
    await heartbeats.insert_one({
        "service_key": service_key,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": metadata or {}
    })


async def get_service_status(service_key: str, min_heartbeats: int = 4) -> ServiceStatusResponse:
    """Get status for a single service based on its heartbeat history"""
    # Get all heartbeats for the service, ordered by timestamp
    cursor = heartbeats.find(
        {"service_key": service_key}
    ).sort("timestamp", -1)  # newest first
    
    heartbeat_records = await cursor.to_list(length=None)
    heartbeat_count = len(heartbeat_records)
    
    if not heartbeat_count:
        return ServiceStatusResponse(
            service_key=service_key,
            status=ServiceStatus.UNKNOWN,
            heartbeat_count=0
        )
    
    # Get the last heartbeat info
    last_heartbeat = heartbeat_records[0]
    last_timestamp = datetime.strptime(last_heartbeat["timestamp"], "%Y-%m-%d %H:%M:%S")
    
    # Calculate time since last heartbeat
    time_since_last = datetime.now() - last_timestamp
    time_since_last_seconds = time_since_last.total_seconds()
    time_since_last_readable = format_timedelta(time_since_last)
    
    # Check if service is dead (no heartbeat in 7 days)
    if time_since_last > timedelta(days=7):
        return ServiceStatusResponse(
            service_key=service_key,
            status=ServiceStatus.DEAD,
            last_heartbeat=last_heartbeat["timestamp"],
            time_since_last_heartbeat_seconds=time_since_last_seconds,
            time_since_last_heartbeat_readable=time_since_last_readable,
            heartbeat_count=heartbeat_count,
            metadata=last_heartbeat.get("metadata")
        )
    
    # If we don't have enough heartbeats, return unknown
    if heartbeat_count < min_heartbeats:
        return ServiceStatusResponse(
            service_key=service_key,
            status=ServiceStatus.UNKNOWN,
            last_heartbeat=last_heartbeat["timestamp"],
            time_since_last_heartbeat_seconds=time_since_last_seconds,
            time_since_last_heartbeat_readable=time_since_last_readable,
            heartbeat_count=heartbeat_count,
            metadata=last_heartbeat.get("metadata")
        )
    
    # Calculate intervals between heartbeats
    intervals = []
    for i in range(heartbeat_count - 1):
        current = datetime.strptime(heartbeat_records[i]["timestamp"], "%Y-%m-%d %H:%M:%S")
        next_beat = datetime.strptime(heartbeat_records[i + 1]["timestamp"], "%Y-%m-%d %H:%M:%S")
        interval = (current - next_beat).total_seconds()
        intervals.append(interval)
    
    # Calculate median interval
    median_interval = statistics.median(intervals)
    
    # Determine status based on time since last heartbeat
    status = (
        ServiceStatus.ALIVE
        if time_since_last_seconds < 2 * median_interval
        else ServiceStatus.DOWN
    )
    
    return ServiceStatusResponse(
        service_key=service_key,
        status=status,
        last_heartbeat=last_heartbeat["timestamp"],
        time_since_last_heartbeat_seconds=time_since_last_seconds,
        time_since_last_heartbeat_readable=time_since_last_readable,
        median_interval=median_interval,
        heartbeat_count=heartbeat_count,
        metadata=last_heartbeat.get("metadata")
    )


async def get_all_services_status(min_heartbeats: int = 4) -> Dict[str, ServiceStatusResponse]:
    """Get status for all services that have ever sent a heartbeat"""
    # Get unique service keys
    service_keys = await heartbeats.distinct("service_key")
    
    # Get status for each service
    services = {}
    for service_key in service_keys:
        status = await get_service_status(service_key, min_heartbeats)
        services[service_key] = status
    
    return services 