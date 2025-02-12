from fastapi import FastAPI, HTTPException
from loguru import logger

from api.models import HeartbeatRequest
from api.db import store_heartbeat

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


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    import uvicorn
    from api.db import settings
    uvicorn.run(app, host=settings.api_host, port=settings.api_port) 