from time import time
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MongoDB settings
    mongodb_url: str
    mongodb_db_name: str

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
client = AsyncIOMotorClient(settings.mongodb_url)
db = client[settings.mongodb_db_name]
heartbeats = db["heartbeats"]


async def store_heartbeat(service_key: str, metadata: Optional[dict] = None) -> None:
    """Store a heartbeat in the database"""
    await heartbeats.insert_one({
        "service_key": service_key,
        "timestamp": time(),
        "metadata": metadata or {}
    }) 