from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict

# Constants for datetime handling
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"  # ISO format with microseconds


def format_datetime(dt: datetime) -> str:
    """Convert datetime to string in our standard format"""
    return dt.strftime(DATETIME_FORMAT)


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime from our standard format"""
    return datetime.strptime(dt_str, DATETIME_FORMAT)


class ServiceType(str, Enum):
    """Type of service being monitored"""
    CLOUD_SERVICE = "cloud_service"  # Long-running cloud service
    LOCAL_JOB = "local_job"  # Periodic local job that can disappear sometimes


class ServiceStatus(str, Enum):
    """Service status based on monitoring"""
    UNKNOWN = "unknown"  # Not enough data (< 4 heartbeats)
    ALIVE = "alive"     # Service is responding within expected period
    DOWN = "down"       # Service is not responding
    DEAD = "dead"       # Service has been down for too long


class HeartbeatRequest(BaseModel):
    service_key: str = Field(..., description="Unique identifier for the service")
    metadata: Optional[dict] = None


class MarkAlertedRequest(BaseModel):
    service_key: str = Field(..., description="Service key to mark as alerted")


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


class Service(BaseModel):
    """Service configuration and current status"""
    service_key: str
    service_type: Optional[ServiceType] = None
    expected_period: Optional[int] = None  # seconds
    dead_after: Optional[int] = None  # seconds
    status: ServiceStatus = ServiceStatus.ALIVE
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict] = None


class StateTransition(BaseModel):
    """Record of service state changes"""
    id: str = Field(alias="_id", default=None)  # MongoDB's ObjectId as string
    service_key: str
    from_state: ServiceStatus
    to_state: ServiceStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    alerted: bool = False
    alert_message: Optional[str] = None  # Additional context for the alert

    class Config:
        json_encoders = {
            datetime: format_datetime
        }
        populate_by_name = True  # Allow both _id and id