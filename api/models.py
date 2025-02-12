from typing import Optional, Dict
from enum import Enum
from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """Service status based on heartbeat history"""
    UNKNOWN = "unknown"  # Not enough data (< 4 heartbeats)
    ALIVE = "alive"     # Recent heartbeat within expected interval
    DOWN = "down"       # No recent heartbeat, but service history exists
    DEAD = "dead"       # No heartbeat in over a week


class HeartbeatRequest(BaseModel):
    service_key: str = Field(..., description="Unique identifier for the service")
    metadata: Optional[dict] = None


class ServiceStatusResponse(BaseModel):
    """Status information for a single service"""
    service_key: str
    status: ServiceStatus
    last_heartbeat: Optional[str] = None
    time_since_last_heartbeat_seconds: Optional[float] = None
    time_since_last_heartbeat_readable: Optional[str] = None
    median_interval: Optional[float] = None
    heartbeat_count: int
    metadata: Optional[Dict] = None


class ServicesStatusResponse(BaseModel):
    """Status information for all services"""
    services: Dict[str, ServiceStatusResponse]