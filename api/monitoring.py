"""Service monitoring logic.

This module is responsible for:
1. Computing current status for each service based on its configuration
2. Detecting state changes and recording transitions
3. Triggering alerts when services go down
"""

from datetime import datetime
from loguru import logger
from typing import Optional, Dict

from api.db import (
    get_all_services,
    upsert_service,
    record_state_transition,
    get_all_services_status,
)
from api.models import Service, ServiceStatus, format_datetime, parse_datetime


def compute_status_from_heartbeats(
    last_heartbeat: datetime,
    median_interval: Optional[float] = None,
    now: Optional[datetime] = None,
) -> ServiceStatus:
    """Compute service status based on heartbeat history"""
    if now is None:
        now = datetime.now()

    time_since_update = (now - last_heartbeat).total_seconds()

    # If no median interval, use default thresholds
    if median_interval is None:
        # Default: DOWN after 15 minutes, DEAD after 7 days
        if time_since_update > 7 * 24 * 3600:  # 7 days
            return ServiceStatus.DEAD
        elif time_since_update > 15 * 60:  # 15 minutes
            return ServiceStatus.DOWN
        else:
            return ServiceStatus.ALIVE

    # Use median-based detection
    if time_since_update > 7 * 24 * 3600:  # 7 days
        return ServiceStatus.DEAD
    elif time_since_update > 2 * median_interval:  # Grace period: 2x median
        return ServiceStatus.DOWN
    else:
        return ServiceStatus.ALIVE


def compute_status_from_config(service: Service, now: Optional[datetime] = None) -> ServiceStatus:
    """Compute service status based on configuration"""
    if now is None:
        now = datetime.now()

    # If service was never updated, consider it DOWN
    if not service.updated_at:
        return ServiceStatus.DOWN

    # Convert string to datetime if needed
    last_update = (
        parse_datetime(service.updated_at)
        if isinstance(service.updated_at, str)
        else service.updated_at
    )

    # Calculate time since last update
    time_since_update = (now - last_update).total_seconds()

    # If no expected_period set, use default thresholds
    if not service.expected_period:
        # Default: DOWN after 15 minutes, DEAD after 7 days
        if time_since_update > 7 * 24 * 3600:  # 7 days
            return ServiceStatus.DEAD
        elif time_since_update > 15 * 60:  # 15 minutes
            return ServiceStatus.DOWN
        else:
            return ServiceStatus.ALIVE

    # Use service-specific thresholds
    expected_period = int(service.expected_period)
    dead_after = (
        int(service.dead_after)
        if service.dead_after
        else expected_period * 7  # Default: 7x expected period
    )

    if time_since_update > dead_after:
        return ServiceStatus.DEAD
    elif time_since_update > expected_period * 2:  # Grace period: 2x expected period
        return ServiceStatus.DOWN
    else:
        return ServiceStatus.ALIVE


async def check_all_services() -> Dict[str, ServiceStatus]:
    """Check status of all services and record state transitions.
    Returns a dict of service keys to their new status (only for changed services)."""
    status_changes = {}

    # Get all registered services and their heartbeat status
    services = await get_all_services()
    heartbeat_statuses = await get_all_services_status()

    for service_key, service in services.items():
        current_status = service.status
        heartbeat_status = heartbeat_statuses.get(service_key)

        # Compute new status
        if service.expected_period:  # Only use config if explicitly set
            computed_status = compute_status_from_config(service)
            logger.debug(
                f"{service_key}: Using configured thresholds. Computed status: {computed_status}"
            )
        else:
            # Use median-based detection from heartbeats
            if not heartbeat_status:
                computed_status = ServiceStatus.UNKNOWN  # No heartbeats = DOWN
                logger.debug(
                    f"{service_key}: No heartbeat status found. Using default: {computed_status}"
                )
            else:
                last_heartbeat = datetime.fromisoformat(str(heartbeat_status.last_heartbeat))
                computed_status = compute_status_from_heartbeats(
                    last_heartbeat, heartbeat_status.median_interval
                )

        if computed_status != current_status:
            # Update service status
            service.status = computed_status
            service.updated_at = datetime.now()
            await upsert_service(service_key=service_key, status=computed_status)

            # Record state transition with message
            alert_message = None
            if computed_status == ServiceStatus.ALIVE:
                alert_message = f"Service {service_key} is back online!"
            elif computed_status in [ServiceStatus.DOWN, ServiceStatus.DEAD]:
                last_seen = (
                    heartbeat_status.last_heartbeat
                    if heartbeat_status
                    else format_datetime(service.updated_at)
                )
                alert_message = (
                    f"Service {service_key} is {computed_status.value}. " f"Last seen: {last_seen}"
                )

            # Record transition (if alerts are enabled)
            transition = await record_state_transition(
                service_key=service_key,
                from_state=current_status,
                to_state=computed_status,
                alert_message=alert_message,
            )
            if transition:
                logger.info(
                    f"Service {service_key} changed status: {current_status} -> {computed_status}"
                )
            else:
                logger.debug(
                    f"Service {service_key} changed status: {current_status} -> {computed_status} "
                    "(alerts disabled)"
                )

            status_changes[service_key] = computed_status

    return status_changes
