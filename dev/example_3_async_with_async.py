import asyncio
from loguru import logger
from api.utils import run_with_heartbeat


async def do_work():
    """Example of an async task doing some work"""
    counter = 0
    while True:
        counter += 1
        logger.info(f"Work iteration {counter}")
        await asyncio.sleep(5)


async def main():
    """Main async function that does work"""
    try:
        await do_work()
    except asyncio.CancelledError:
        logger.info("Work cancelled, shutting down...")


if __name__ == "__main__":
    run_with_heartbeat(
        main(),
        service_key="example-async-service",
        period=60
    )
