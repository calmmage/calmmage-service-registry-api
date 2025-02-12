import time
from loguru import logger
from api.utils import heartbeat_for_sync


@heartbeat_for_sync(service_key="example-sync-service", period=60)
def main():
    """Main synchronous function that does some work while heartbeat runs in background"""
    try:
        while True:
            logger.info("Main thread doing some work...")
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
