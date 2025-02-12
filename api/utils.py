import asyncio
import os
import threading
import time
from functools import wraps
from typing import Optional, Callable, Any, Coroutine
import httpx
from loguru import logger


def get_api_url() -> Optional[str]:
    """Get API URL from environment variable"""
    url = os.getenv("CALMMAGE_SERVICE_REGISTRY_URL")
    if not url:
        logger.warning("CALMMAGE_SERVICE_REGISTRY_URL not set in environment")
    return url


def heartbeat(service_key: str, period: int = 300) -> None:
    """Run heartbeat loop in current thread. Default period is 5 minutes."""
    api_url = get_api_url()
    if not api_url:
        logger.warning("Heartbeat disabled: CALMMAGE_SERVICE_REGISTRY_URL not set")
        return

    logger.info(f"Starting heartbeat service for {service_key}")
    logger.info(f"Sending heartbeat every {period} seconds")

    while True:
        try:
            response = httpx.post(
                f"{api_url}/heartbeat",
                json={"service_key": service_key}
            )
            response.raise_for_status()
            logger.info(f"Heartbeat sent for {service_key}")
        except Exception as e:
            logger.error(f"Failed to send heartbeat for {service_key}: {e}")
        
        try:
            time.sleep(period)
        except KeyboardInterrupt:
            logger.info("Heartbeat service interrupted")
            break


async def aheartbeat(service_key: str, period: int = 300) -> None:
    """Run heartbeat loop asynchronously. Default period is 5 minutes."""
    api_url = get_api_url()
    if not api_url:
        logger.warning("Heartbeat disabled: CALMMAGE_SERVICE_REGISTRY_URL not set")
        return

    logger.info(f"Starting heartbeat service for {service_key}")
    logger.info(f"Sending heartbeat every {period} seconds")

    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_url}/heartbeat",
                    json={"service_key": service_key}
                )
                response.raise_for_status()
                logger.info(f"Heartbeat sent for {service_key}")
        except Exception as e:
            logger.error(f"Failed to send heartbeat for {service_key}: {e}")
        
        try:
            await asyncio.sleep(period)
        except asyncio.CancelledError:
            logger.info("Heartbeat service cancelled")
            break


def heartbeat_for_sync(service_key: str, period: int = 300) -> Callable:
    """Decorator that runs heartbeat in background thread for sync functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Start heartbeat in background thread
            thread = threading.Thread(
                target=heartbeat,
                args=(service_key, period),
                daemon=True
            )
            thread.start()
            logger.info(f"Started heartbeat service for {service_key} in background")
            
            # Run the main function
            return func(*args, **kwargs)
        return wrapper
    return decorator


def run_with_heartbeat(
    coro: Coroutine,
    service_key: str,
    period: int = 300,
    debug: bool = False
) -> None:
    """
    Run an async function with a heartbeat service.
    Similar to asyncio.run but adds a heartbeat service.
    
    Args:
        coro: The coroutine to run
        service_key: Service identifier for heartbeat
        period: Heartbeat interval in seconds (default: 5 minutes)
        debug: Enable asyncio debug mode
    """
    async def _run_with_heartbeat():
        # Create heartbeat task
        heartbeat_task = asyncio.create_task(aheartbeat(service_key, period))
        logger.info(f"Started heartbeat service for {service_key} in background")
        
        try:
            # Run both the heartbeat and the main coroutine
            main_task = asyncio.create_task(coro)
            await asyncio.gather(heartbeat_task, main_task)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled")
            raise
        finally:
            # Ensure heartbeat is cancelled when main task ends
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    try:
        asyncio.run(_run_with_heartbeat(), debug=debug)
    except KeyboardInterrupt:
        logger.info("Shutting down...") 