# Reworking Service Registry Alert System
We're reworking the service registry alert system to track state switches rather than just reporting currently down servers. We'll add two new collections: one for aggregated service data (service list with current status) and one for state transitions (historical state changes). The Telegram bot will later consume this data to deliver precise alerts.

## aggregated services
- [x] create service model in api/models.py (fields: service_key, last_known_status, last_heartbeat, etc)
- [x] REVISION NEEDED: simplify Service model to only essential fields
- [x] ENHANCEMENT: add service_type and timing configuration
- [x] implement upsert_service() in api/db.py (insert/update record in "services" collection)
- [x] add get_all_services() in api/db.py (retrieve aggregated service records)
- [x] add test endpoints in main.py

### Test Instructions
```bash
# Test cloud service with default settings
curl -X POST "http://localhost:8000/test/update-service/cloud-service?status=alive"

# Test cloud service with custom period (5 minutes)
curl -X POST "http://localhost:8000/test/update-service/cloud-service-custom?status=alive&expected_period=300"

# Test local job (daily)
curl -X POST "http://localhost:8000/test/update-service/daily-job?status=alive&service_type=local_job&expected_period=86400"

# Get all services
curl "http://localhost:8000/services"
```

### Python Monitor Usage
```python
from api.utils.service_monitor import monitor_service, monitor_local_job, run_with_monitor

# Monitor cloud service
monitor_service("my-service", expected_period=300)  # 5 minutes

# Monitor local job
@monitor_local_job("daily-job", expected_period=24*3600)  # 24 hours
def daily_task():
    process_data()

# Monitor async service
async def my_service():
    while True:
        await process_data()
        await asyncio.sleep(5)

run_with_monitor(
    my_service(),
    "my-async-service",
    expected_period=300
)
```

## state transitions
- [ ] define state_transition model in api/models.py (fields: service_key, from_state, to_state, timestamp, alert_sent)
- [ ] implement record_state_transition() in api/db.py (log transition events in "state_transitions" collection)

## monitoring
- [ ] build monitoring job in api/monitoring.py (compute current status from raw heartbeats)
- [ ] compare computed status with stored service record; update service and record state transition if changed
- [ ] schedule monitoring job as a periodic background task

## api integration
- [ ] add /state-history endpoint in api/main.py (return state transitions)
- [ ] hook monitoring job into startup event in api/main.py

## bot integration
- [ ] update bot scheduled_tasks.py (poll /state-history endpoint for new transitions)
- [ ] modify telegram alert logic to deliver alerts based on state transitions