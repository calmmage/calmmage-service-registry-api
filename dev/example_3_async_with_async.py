import asyncio
from loguru import logger
from api.utils import heartbeat_for_async


async def do_work():
    """Example of an async task doing some work"""
    counter = 0
    while True:
        counter += 1
        logger.info(f"Work iteration {counter}")
        await asyncio.sleep(5)


@heartbeat_for_async(service_key="example-async-service", period=60)
async def main():
    """Main async function that does work while heartbeat runs in parallel"""
    try:
        await do_work()
    except asyncio.CancelledError:
        logger.info("Work cancelled, shutting down...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
