import time
import requests
from loguru import logger


def send_heartbeat(service_key: str, api_url: str = "http://localhost:8765") -> None:
    """Send a heartbeat to the service registry"""
    try:
        response = requests.post(
            f"{api_url}/heartbeat",
            json={"service_key": service_key}
        )
        response.raise_for_status()
        logger.info(f"Heartbeat sent for {service_key}")
    except Exception as e:
        logger.error(f"Failed to send heartbeat for {service_key}: {e}")


def main():
    service_key = "example-sync-service"
    interval = 60  # seconds

    logger.info(f"Starting heartbeat service for {service_key}")
    logger.info(f"Sending heartbeat every {interval} seconds")

    while True:
        send_heartbeat(service_key)
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
