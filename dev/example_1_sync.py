from loguru import logger
from api.utils import heartbeat


def main():
    """Simple sync service that just runs heartbeat"""
    service_key = "example-sync-service"
    try:
        # This will run forever until interrupted
        heartbeat(service_key, period=60)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
