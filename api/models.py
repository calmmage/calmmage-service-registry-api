from typing import Optional
from pydantic import BaseModel, Field
# from datetime import datetime, timezone


class HeartbeatRequest(BaseModel):
    service_key: str = Field(..., description="Unique identifier for the service")
    metadata: Optional[dict] = None

    # class Config:
    #     json_encoders = {
    #         # Ensure all datetime objects are serialized in UTC
    #         datetime: lambda dt: dt.astimezone(timezone.utc).isoformat()
    #     } 