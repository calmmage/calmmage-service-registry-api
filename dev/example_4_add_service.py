from api.utils.service_config import add_service

if __name__ == "__main__":
    # Configure a cloud service (5-minute heartbeat)
    add_service(
        "my-api",
        expected_period=300,  # 5 minutes
        dead_after=7*24*3600  # 7 days
    )
        
    # Configure a daily job
    add_service(
        "daily-cleanup",
        service_type="local_job",
        expected_period=24*3600,  # 24 hours
        dead_after=2*24*3600  # Consider dead after 2 days
    )