# Reworking Service Registry Alert System
We're reworking the service registry alert system to track state switches rather than just reporting currently down servers. We'll add two new collections: one for aggregated service data (service list with current status) and one for state transitions (historical state changes). The Telegram bot will later consume this data to deliver precise alerts.

## aggregated services
- [x] create service model in api/models.py (fields: service_key, last_known_status, last_heartbeat, etc)
- [ ] implement upsert_service() in api/db.py (insert/update record in "services" collection)
- [ ] add get_all_services() in api/db.py (retrieve aggregated service records)

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

## verification
- [ ] ensure heartbeat saving logic remains unchanged

- [x] 6) a scheduled job (daily) to check status of all services and elevate the ones that require attention
  - [ ] how do i check this actually works? need some dev mode with custom time - very soon. Also - ... 

- [x] 7) When server goes down - alert the user
logic is similar to 6 - just a scheduled job every 15 minutes or so. If failed -> writes to user.
- [ ] only alert the user one time - first time the service is down. How do we track that?
- [x] for now - add the first service: the bot itself.

- [x] 9) add / move utils - decorators etc - to calmlib
 - [canceled] create calmlib / all.py where we import all the useful utils? or just do it in utils/init.py?
 - [ ] add examples to calmlib? 
 - [ ] ask gpt: "I keep forgetting / getting lost in all the utils. Any suggestions? Here's file tree. I import all the utils to calmlib/utils/init.py"

- 10) Send alerts to notification-manager bot, that takes care of my attention - instead of directly to telegram
- 11) write and launch notification-manager bot

## Workalong

1 - heartbeat handle.
Seems to be there.

Test manually? how? CURL POST request to http://localhost:8000/heartbeat?service_key=test

: curl -X POST http://localhost:8765/heartbeat?service_key=test


2 - sample service

```
Old env file - showcases features
CHECK_INTERVAL_SECONDS=60
DAILY_SUMMARY_INTERVAL_SECONDS=86400
DAILY_SUMMARY_TIME=09:00
DATABASE_NAME=service_registry
DEBUG_MODE=False
MONGODB_URL=mongodb://localhost:27017
SERVICE_INACTIVE_THRESHOLD_MINUTES=15

TELEGRAM_CHAT_ID=291560340
TIMEZONE=Europe/Moscow
```


# Done


What am I doing with this?

- [x] 1) just a /heartbeat (service_key) handle
  - [x] make timestamp a readable str
- [x] 2) -> write to db

- [x] 3) a sample service that can call this api to register itself every 5 minutes
  - [x] write a util func and a decorator to apply on top of main func
    - heartbeat
    - aheartbeat
    - heartbeat_for_sync
    - heartbeat_for_async

- [x] 4) api handle to get status of all services
  Logic:
  - for each service:
  - check if > than 3-4 historical heartbeats available
  - less than 4: -> 'unknown' / 'waiting for more data' 
  - if more: use median time difference between heartbeats 
  - 
  - based on that: 'alive' / 'down' / 'dead' (this is enum)
  - alive: < 2 * median time since last heartbeat
  - down: > 2 * median time since last heartbeat
  - dead: - like a week.
  - if no heartbeat in last 7 days: dead

-[x] 5) telegram command to get status of all services
  - [x] let's actually split the command into two: - status and status_full 
  for full: include dead, include additional info

-> calls the api by the specified url of this service to get statuses of all services

- [x] 8) launch bot and api on coolify