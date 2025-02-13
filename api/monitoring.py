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
    get_all_services, upsert_service,
    record_state_transition
)
from api.models import (
    Service, ServiceStatus, format_datetime, parse_datetime
)


def compute_status_from_heartbeats(
    last_heartbeat: datetime,
    median_interval: Optional[float] = None,
    now: Optional[datetime] = None
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


def compute_status_from_config(
    service: Service,
    now: Optional[datetime] = None
) -> ServiceStatus:
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
    
    # Get all registered services
    services = await get_all_services()
    
    for service_key, service in services.items():
        current_status = service.status
        
        # Compute new status based on service configuration
        computed_status = compute_status_from_config(service)
        
        if computed_status != current_status:
            # Update service status
            service.status = computed_status
            service.updated_at = datetime.now()
            await upsert_service(
                service_key=service_key,
                status=computed_status
            )
            
            # Record state transition with message
            alert_message = None
            if computed_status == ServiceStatus.ALIVE:
                alert_message = f"Service {service_key} is back online!"
            elif computed_status in [ServiceStatus.DOWN, ServiceStatus.DEAD]:
                alert_message = (
                    f"Service {service_key} is {computed_status.value}. "
                    f"Last seen: {format_datetime(service.updated_at)}"
                )
            
            await record_state_transition(
                service_key=service_key,
                from_state=current_status,
                to_state=computed_status,
                alert_message=alert_message
            )
            
            status_changes[service_key] = computed_status
            logger.info(f"Service {service_key} changed status: {current_status} -> {computed_status}")
    
    return status_changes 