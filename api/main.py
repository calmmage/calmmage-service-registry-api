from fastapi import FastAPI, HTTPException
from loguru import logger

from api.models import HeartbeatRequest, ServicesStatusResponse
from api.db import store_heartbeat, get_all_services_status

app = FastAPI(title="Service Registry API")


@app.post("/heartbeat")
async def heartbeat(request: HeartbeatRequest) -> dict:
    """Record a service heartbeat"""
    try:
        await store_heartbeat(
            service_key=request.service_key,
            metadata=request.metadata
        )
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


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    import uvicorn
    from api.db import settings
    uvicorn.run(app, host=settings.api_host, port=settings.api_port) 