import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel
from typing import Optional, Dict, Set

from api.db import (
    get_all_services,
    get_service,
    get_state_transitions,
    store_heartbeat,
    get_all_services_status,
    mark_service_transitions_alerted,
    upsert_service,
    db,
)
from api.models import (
    Service,
    ServiceType,
    ServiceStatus,
    StateTransition,
    HeartbeatRequest,
    ServicesStatusResponse,
    MarkAlertedRequest,
    format_datetime,
)
from api.monitoring import check_all_services

app = FastAPI(title="Service Registry API")


# In-memory cache of known services
known_services: Set[str] = set()


async def load_known_services():
    """Load known services into memory"""
    services = await get_all_services()
    known_services.update(services.keys())
    logger.info(f"Loaded {len(known_services)} known services")


# Heartbeat


@app.post("/heartbeat")
async def heartbeat(request: HeartbeatRequest) -> dict:
    """Record a service heartbeat. Creates service if it doesn't exist."""
    try:
        # Create service if it doesn't exist
        if request.service_key not in known_services:
            logger.info(f"New service detected: {request.service_key}")
            # Generate default display name from service key
            display_name = request.service_key.replace("-", " ").replace("_", " ").title()
            # Initialize new service with all default values
            service = Service(
                service_key=request.service_key,
                display_name=display_name,
                status=ServiceStatus.ALIVE,
                alerts_enabled=True,
                service_group="default",
                updated_at=datetime.now(),
            )
            update_data = service.model_dump()
            # Convert datetime and enums to MongoDB format
            if "updated_at" in update_data:
                update_data["updated_at"] = format_datetime(update_data["updated_at"])
            if "service_type" in update_data and update_data["service_type"] is not None:
                update_data["service_type"] = update_data["service_type"].value
            if "status" in update_data:
                update_data["status"] = update_data["status"].value
            await db.services.insert_one(update_data)
            known_services.add(request.service_key)

        # Store heartbeat
        await store_heartbeat(service_key=request.service_key, metadata=request.metadata)
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Failed to store heartbeat")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=ServicesStatusResponse)
async def get_status() -> ServicesStatusResponse:
    """Get status of all registered services"""
    try:
        services = await get_all_services_status()
        return ServicesStatusResponse(services=services)
    except Exception as e:
        logger.exception("Failed to get services status")
        raise HTTPException(status_code=500, detail=str(e))


# Service Configuration


class ServiceRequest(BaseModel):
    """Request model for service configuration"""

    service_key: str
    service_type: Optional[ServiceType] = None
    service_group: Optional[str] = None
    expected_period: Optional[int] = None
    dead_after: Optional[int] = None
    alerts_enabled: Optional[bool] = None
    display_name: Optional[str] = None
    metadata: Optional[Dict] = None


@app.post("/configure-service")
async def configure_service(request: ServiceRequest) -> Service:
    """Configure a service with monitoring parameters"""
    try:
        service = await upsert_service(
            service_key=request.service_key,
            service_type=request.service_type,
            service_group=request.service_group,
            expected_period=request.expected_period,
            dead_after=request.dead_after,
            alerts_enabled=request.alerts_enabled,
            display_name=request.display_name,
            metadata=request.metadata,
        )
        known_services.add(request.service_key)
        return service
    except Exception as e:
        logger.exception("Failed to configure service")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services", response_model=Dict[str, Service])
async def list_services() -> Dict[str, Service]:
    """List all configured services"""
    try:
        services = await get_all_services()
        # Update known services cache
        known_services.update(services.keys())
        return services
    except Exception as e:
        logger.exception("Failed to list services")
        raise HTTPException(status_code=500, detail=str(e))


class GetServiceRequest(BaseModel):
    """Request model for getting service info"""

    service_key: str


@app.post("/get-service", response_model=Optional[Service])
async def get_service_info(request: GetServiceRequest) -> Optional[Service]:
    """Get service info by key"""
    try:
        return await get_service(request.service_key)
    except Exception as e:
        logger.exception("Failed to get service")
        raise HTTPException(status_code=500, detail=str(e))


# State History


class GetStateTransitionsRequest(BaseModel):
    """Request model for getting state transitions"""

    service_key: Optional[str] = None
    limit: int = 100
    only_not_alerted: bool = False


@app.post("/state-transitions", response_model=Dict[str, StateTransition])
async def get_all_services_history(
    request: GetStateTransitionsRequest,
) -> Dict[str, StateTransition]:
    """Get state transition history for all services or a specific service"""
    try:
        logger.info(f"Getting services history. Params: {request}")
        transitions = await get_state_transitions(
            service_key=request.service_key,
            limit=request.limit,
            only_not_alerted=request.only_not_alerted,
        )
        result = transitions or {}
        logger.info(f"Found {len(result)} transitions")
        logger.debug(f"Transitions data: {result}")
        return result
    except Exception as e:
        logger.exception("Failed to get services history")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mark-alerted")
async def mark_service_alerted(request: MarkAlertedRequest) -> dict:
    """Mark all unalerted state transitions for a service as alerted"""
    try:
        modified_count = await mark_service_transitions_alerted(request.service_key)
        return {"status": "ok", "transitions_marked": modified_count}
    except Exception as e:
        logger.exception("Failed to mark service transitions as alerted")
        raise HTTPException(status_code=500, detail=str(e))


# Monitoring


async def monitor_services_periodically():
    """Background task to monitor services periodically"""
    while True:
        try:
            status_changes = await check_all_services()
            if status_changes:
                logger.info(f"Status changes detected: {status_changes}")
        except Exception as e:
            logger.exception("Error in monitoring task")

        from api.db import settings

        await asyncio.sleep(settings.monitoring_interval_seconds)  # Use configured interval


@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    await load_known_services()
    asyncio.create_task(monitor_services_periodically())


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    import uvicorn
    from api.db import settings

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
