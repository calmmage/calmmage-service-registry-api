from fastapi import FastAPI, HTTPException
from loguru import logger

from api.models import HeartbeatRequest, ServiceStatus
from api.db import store_heartbeat, get_service_status, get_all_services

app = FastAPI(title="Service Registry API")


@app.post("/heartbeat")
async def heartbeat(request: HeartbeatRequest) -> dict:
    """Record a service heartbeat"""
    try:
        await store_heartbeat(
            service_key=request.service_key,
            timestamp=request.timestamp,
            metadata=request.metadata
        )
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Failed to store heartbeat")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/service/{service_key}/status")
async def get_status(service_key: str) -> ServiceStatus:
    """Get the status of a specific service"""
    try:
        status = await get_service_status(service_key)
        if status is None:
            raise HTTPException(status_code=404, detail="Service not found")
        return ServiceStatus(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get service status")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services")
async def list_services() -> list[str]:
    """Get a list of all registered services"""
    try:
        return await get_all_services()
    except Exception as e:
        logger.exception("Failed to list services")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
