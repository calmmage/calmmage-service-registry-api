import asyncio
import threading
import time
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


def run_heartbeat_in_thread(service_key: str, interval: int = 60) -> threading.Thread:
    """Run heartbeat loop in a background thread"""
    def _run_async_loop():
        asyncio.run(heartbeat_loop(service_key, interval))

    thread = threading.Thread(target=_run_async_loop, daemon=True)
    thread.start()
    return thread


def main():
    """Main synchronous function that does some work while heartbeat runs in background"""
    service_key = "example-async-bg-service"
    
    # Start heartbeat in background
    heartbeat_thread = run_heartbeat_in_thread(service_key)
    
    # Do some work in main thread
    try:
        while True:
            logger.info("Main thread doing some work...")
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
