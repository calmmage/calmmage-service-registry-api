import asyncio
from typing import Optional

import httpx
from loguru import logger


async def send_heartbeat(service_key: str, api_url: str = "http://localhost:8765") -> None:
    """Send a heartbeat to the service registry"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{api_url}/heartbeat",
                json={"service_key": service_key}
            )
            response.raise_for_status()
            logger.info(f"Heartbeat sent for {service_key}")
        except Exception as e:
            logger.error(f"Failed to send heartbeat for {service_key}: {e}")


async def heartbeat_loop(service_key: str, interval: int = 60):
    """Async loop that sends heartbeats"""
    logger.info(f"Starting heartbeat service for {service_key}")
    logger.info(f"Sending heartbeat every {interval} seconds")

    while True:
        await send_heartbeat(service_key)
        await asyncio.sleep(interval)


async def some_async_work():
    """Example of another async task running in parallel"""
    counter = 0
    while True:
        counter += 1
        logger.info(f"Async work iteration {counter}")
        await asyncio.sleep(2)


async def main():
    """Main async function that runs heartbeat and other tasks"""
    service_key = "example-async-service"
    
    # Create tasks
    heartbeat_task = asyncio.create_task(heartbeat_loop(service_key))
    work_task = asyncio.create_task(some_async_work())
    
    try:
        # Wait for both tasks forever
        await asyncio.gather(heartbeat_task, work_task)
    except asyncio.CancelledError:
        logger.info("Tasks cancelled, shutting down...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
