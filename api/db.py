import logging
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
from typing import Dict, Optional

from api.models import (
    Service,
    ServiceType,
    ServiceStatus,
    StateTransition,
    ServiceStatusResponse,
    format_datetime,
)


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "service_registry"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    monitoring_interval_seconds: int = 60  # How often to check service status

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
client = AsyncIOMotorClient(settings.mongodb_url)
db = client[settings.mongodb_db_name]

logger = logging.getLogger(__name__)


# Legacy Heartbeat Functions


async def store_heartbeat(service_key: str, metadata: Optional[dict] = None) -> None:
    """Store a service heartbeat"""
    heartbeat = {
        "service_key": service_key,
        "timestamp": format_datetime(datetime.now()),
        "metadata": metadata,
    }
    await db.heartbeats.insert_one(heartbeat)


def _compute_time_since_last_heartbeat(last_heartbeat: datetime) -> tuple[float, str]:
    """Helper to compute time since last heartbeat"""
    now = datetime.now()
    delta = now - last_heartbeat
    seconds = delta.total_seconds()

    if seconds < 60:
        readable = f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        readable = f"{minutes} minutes"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        readable = f"{hours} hours"
    else:
        days = int(seconds / 86400)
        readable = f"{days} days"

    return seconds, readable


async def get_all_services_status() -> Dict[str, ServiceStatusResponse]:
    """Get status of all services based on heartbeat history"""
    # Only look at heartbeats from last 7 days
    cutoff_time = format_datetime(datetime.now() - timedelta(days=7))

    # Get all unique service keys with recent heartbeats
    service_keys = set()
    async for heartbeat in db.heartbeats.find({"timestamp": {"$gte": cutoff_time}}):
        service_keys.add(heartbeat["service_key"])

    # Compute status for each service
    services = {}
    for service_key in service_keys:
        # Get recent heartbeats for this service
        heartbeats = []
        cursor = db.heartbeats.find(
            {"service_key": service_key, "timestamp": {"$gte": cutoff_time}}
        ).sort("timestamp", -1)
        async for heartbeat in cursor:
            heartbeats.append(heartbeat)

        # Compute status
        status = ServiceStatus.UNKNOWN
        last_heartbeat = None
        time_since_last_heartbeat_seconds = None
        time_since_last_heartbeat_readable = None
        median_interval = None
        metadata = None

        if heartbeats:
            # Get last heartbeat info
            last_heartbeat = datetime.fromisoformat(heartbeats[0]["timestamp"])
            time_since_last_heartbeat_seconds, time_since_last_heartbeat_readable = (
                _compute_time_since_last_heartbeat(last_heartbeat)
            )
            metadata = heartbeats[0].get("metadata")

            # Compute status based on heartbeat history
            if len(heartbeats) >= 4:
                # Calculate intervals between heartbeats
                intervals = []
                for i in range(len(heartbeats) - 1):
                    current = datetime.fromisoformat(heartbeats[i]["timestamp"])
                    next_hb = datetime.fromisoformat(heartbeats[i + 1]["timestamp"])
                    intervals.append((current - next_hb).total_seconds())

                # Use median interval to determine expected frequency
                intervals.sort()
                median_interval = intervals[len(intervals) // 2]

                # Status based on time since last heartbeat
                if time_since_last_heartbeat_seconds > 7 * 24 * 3600:  # 7 days
                    status = ServiceStatus.DEAD
                elif time_since_last_heartbeat_seconds > 2 * median_interval:
                    status = ServiceStatus.DOWN
                else:
                    status = ServiceStatus.ALIVE
            else:
                # Not enough data for median-based detection
                if time_since_last_heartbeat_seconds > 7 * 24 * 3600:  # 7 days
                    status = ServiceStatus.DEAD
                elif time_since_last_heartbeat_seconds > 15 * 60:  # 15 minutes
                    status = ServiceStatus.DOWN
                else:
                    status = ServiceStatus.ALIVE

        services[service_key] = ServiceStatusResponse(
            service_key=service_key,
            status=status,
            last_heartbeat=last_heartbeat.isoformat() if last_heartbeat else None,
            time_since_last_heartbeat_seconds=time_since_last_heartbeat_seconds,
            time_since_last_heartbeat_readable=time_since_last_heartbeat_readable,
            median_interval=median_interval,
            heartbeat_count=len(heartbeats),
            metadata=metadata,
        )

    return services


async def cleanup_old_heartbeats(days: int = 30) -> int:
    """Remove heartbeats older than specified days.
    Returns number of heartbeats removed."""
    cutoff_time = format_datetime(datetime.now() - timedelta(days=days))
    result = await db.heartbeats.delete_many({"timestamp": {"$lt": cutoff_time}})
    return result.deleted_count


# Service Configuration


async def upsert_service(
    service_key: str,
    service_type: Optional[ServiceType] = None,
    expected_period: Optional[int] = None,
    dead_after: Optional[int] = None,
    status: Optional[ServiceStatus] = None,
) -> Service:
    """Configure a service"""
    update_data = {"service_key": service_key}
    if service_type is not None:
        update_data["service_type"] = service_type.value
    if expected_period is not None:
        update_data["expected_period"] = str(expected_period)
    if dead_after is not None:
        update_data["dead_after"] = str(dead_after)
    if status is not None:
        update_data["status"] = status.value
        update_data["updated_at"] = format_datetime(datetime.now())

    result = await db.services.update_one(
        {"service_key": service_key}, {"$set": update_data}, upsert=True
    )

    if result.upserted_id or result.modified_count > 0:
        service_data = await db.services.find_one({"service_key": service_key})
        if not service_data:
            raise ValueError(f"Failed to retrieve service after upsert: {service_key}")
        return Service(**service_data)
    else:
        raise ValueError(f"Failed to upsert service: {service_key}")


async def get_all_services() -> Dict[str, Service]:
    """Get all configured services"""
    services = {}
    async for service_data in db.services.find():
        service = Service(**service_data)
        services[service.service_key] = service
    return services


async def get_service(service_key: str) -> Optional[Service]:
    """Get a service by key"""
    service_data = await db.services.find_one({"service_key": service_key})
    return Service(**service_data) if service_data else None


# State Transitions


async def record_state_transition(
    service_key: str,
    from_state: ServiceStatus,
    to_state: ServiceStatus,
    alert_message: Optional[str] = None,
) -> StateTransition:
    """Record a service state transition"""
    transition = StateTransition(
        service_key=service_key,
        from_state=from_state,
        to_state=to_state,
        alert_message=alert_message,
        timestamp=datetime.now(),  # Explicitly set to ensure consistency
    )

    # Convert to dict and ensure datetime is formatted correctly
    transition_data = transition.model_dump()
    transition_data["timestamp"] = format_datetime(transition.timestamp)

    logger.debug(f"Recording state transition: {transition_data}")
    await db.state_transitions.insert_one(transition_data)
    return transition


async def get_state_transitions(
    service_key: Optional[str] = None, limit: int = 100, only_not_alerted: bool = False
) -> Dict[str, StateTransition]:
    """Get state transitions, optionally filtered by service and alert status"""
    query = {}
    if service_key:
        query["service_key"] = service_key
    if only_not_alerted:
        query["alerted"] = False

    logger.debug(f"Fetching state transitions with query: {query}")
    transitions = []
    cursor = db.state_transitions.find(query).sort("timestamp", -1).limit(limit)
    async for transition_data in cursor:
        # Convert ObjectId to string
        transition_data["_id"] = str(transition_data["_id"])
        logger.debug(f"Found transition: {transition_data}")
        transitions.append(StateTransition(**transition_data))
    logger.debug(f"Retrieved {len(transitions)} transitions")

    result = {}
    for transition in sorted(transitions, key=lambda x: x.timestamp):
        result[transition.service_key] = transition
    return result


async def mark_service_transitions_alerted(service_key: str) -> int:
    """Mark all unalerted state transitions for a service as alerted.
    Returns the number of transitions marked as alerted."""
    result = await db.state_transitions.update_many(
        {"service_key": service_key, "alerted": False}, {"$set": {"alerted": True}}
    )
    return result.modified_count
