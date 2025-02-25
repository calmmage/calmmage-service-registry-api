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

    # Get all services configuration
    services = {}
    async for service_data in db.services.find():
        services[service_data["service_key"]] = Service(**service_data)

    # Get all unique service keys with recent heartbeats
    service_keys = set()
    async for heartbeat in db.heartbeats.find({"timestamp": {"$gte": cutoff_time}}):
        service_keys.add(heartbeat["service_key"])

    # Compute status for each service
    services_status = {}
    for service_key in service_keys:
        # Get recent heartbeats for this service
        heartbeats = []
        cursor = db.heartbeats.find(
            {"service_key": service_key, "timestamp": {"$gte": cutoff_time}}
        ).sort("timestamp", -1)
        async for heartbeat in cursor:
            heartbeats.append(heartbeat)

        # Get or create service record
        service = services.get(service_key)
        if not service:
            # Create new service with default values if not found
            service = Service(service_key=service_key)
            services[service_key] = service

        # Compute time since last heartbeat if we have any
        last_heartbeat = None
        time_since_last_heartbeat_seconds = None
        time_since_last_heartbeat_readable = None
        median_interval = None

        if heartbeats:
            # Get last heartbeat info
            last_heartbeat = datetime.fromisoformat(heartbeats[0]["timestamp"])
            time_since_last_heartbeat_seconds, time_since_last_heartbeat_readable = (
                _compute_time_since_last_heartbeat(last_heartbeat)
            )

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

        services_status[service_key] = ServiceStatusResponse(
            service=service,
            last_heartbeat=last_heartbeat.isoformat() if last_heartbeat else None,
            time_since_last_heartbeat_seconds=time_since_last_heartbeat_seconds,
            time_since_last_heartbeat_readable=time_since_last_heartbeat_readable,
            median_interval=median_interval,
            heartbeat_count=len(heartbeats),
        )

    return services_status


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
    service_group: Optional[str] = None,
    expected_period: Optional[int] = None,
    dead_after: Optional[int] = None,
    status: Optional[ServiceStatus] = None,
    alerts_enabled: Optional[bool] = None,
    display_name: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Service:
    """Configure a service"""
    # Only include fields that were explicitly provided
    update_data = {}

    if service_type is not None:
        update_data["service_type"] = service_type.value if service_type else None
    if service_group is not None:
        update_data["service_group"] = service_group
    if expected_period is not None:
        update_data["expected_period"] = expected_period
    if dead_after is not None:
        update_data["dead_after"] = dead_after
    if status is not None:
        update_data["status"] = status.value
        update_data["updated_at"] = format_datetime(datetime.now())
    if alerts_enabled is not None:
        update_data["alerts_enabled"] = alerts_enabled
    if display_name is not None:
        update_data["display_name"] = display_name
    if metadata is not None:
        update_data["metadata"] = metadata

    # Update in MongoDB
    result = await db.services.update_one(
        {"service_key": service_key}, {"$set": update_data}, upsert=False
    )

    if result.modified_count > 0:
        service_data = await db.services.find_one({"service_key": service_key})
        if not service_data:
            raise ValueError(f"Failed to retrieve service after update: {service_key}")
        return Service(**service_data)
    else:
        raise ValueError(f"Failed to update service: {service_key}")


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
) -> Optional[StateTransition]:
    """Record a service state transition.

    Returns:
        StateTransition if alerts are enabled for the service, None otherwise.
    """
    # Check if alerts are enabled for this service
    service = await get_service(service_key)
    if not service or not service.alerts_enabled:
        logger.debug(
            f"Alerts disabled for service {service_key}, skipping state transition recording"
        )
        return None

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
