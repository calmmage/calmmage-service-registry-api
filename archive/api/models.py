from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HeartbeatRequest(BaseModel):
    service_key: str = Field(..., description="Unique identifier for the service")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the heartbeat")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata about the service")


class ServiceStatus(BaseModel):
    service_key: str
    last_heartbeat: datetime
    state: str  # "ok" / "down" / "dead"
    median_interval: float  # in seconds
    metadata: Optional[dict] = None 