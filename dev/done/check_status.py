#!/usr/bin/env python3
import httpx
import os
from loguru import logger


def get_api_url() -> str:
    """Get API URL from environment variable or use default"""
    return os.getenv("CALMMAGE_SERVICE_REGISTRY_URL", "http://localhost:8765")


def format_service_status(service_key: str, status_data: dict) -> str:
    """Format a single service status into a readable string"""
    status = status_data["status"]
    last_beat = status_data.get("last_heartbeat", "never")
    count = status_data["heartbeat_count"]
    interval = status_data.get("median_interval")
    time_since = status_data.get("time_since_last_heartbeat_readable", "never")

    # Format interval if available
    interval_str = f", interval: {interval:.1f}s" if interval else ""

    return (
        f"{service_key:30} | "
        f"Status: {status:7} | "
        f"Last seen: {time_since:10} ago | "
        f"Count: {count}{interval_str}"
    )


def main():
    """Check and display status of all services"""
    api_url = get_api_url()
    logger.info(f"Checking services status at {api_url}")

    try:
        response = httpx.get(f"{api_url}/status")
        response.raise_for_status()
        data = response.json()

        # Print header
        print("\nServices Status:")
        print("-" * 80)

        # Print each service status
        services = data["services"]
        if not services:
            print("No services registered yet.")
            return

        for service_key, status_data in sorted(services.items()):
            print(format_service_status(service_key, status_data))

    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        exit(1)


if __name__ == "__main__":
    main()
