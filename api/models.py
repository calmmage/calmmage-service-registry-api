from typing import Optional
from pydantic import BaseModel, Field


class HeartbeatRequest(BaseModel):
    service_key: str = Field(..., description="Unique identifier for the service")
    metadata: Optional[dict] = None