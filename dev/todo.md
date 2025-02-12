What am I doing with this?

- [x] 1) just a /heartbeat (service_key) handle
  - [ ] make timestamp a readable str
- [x] 2) -> write to db

- [x] 3) a sample service that can call this api to register itself every 5 minutes
  - [ ] write a util func and a decorator to apply on top of main func
    - heartbeat
    - aheartbeat
    - heartbeat_for_sync
    - heartbeat_for_async

4) api handle to get status of all services
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

5) telegram command to get status of all services

-> calls the api by the specified url of this service to get statuses of all services

6) a scheduled job (daily) to check

## Workalong

1 - heartbeat handle.
Seems to be there.

Test manually? how? CURL POST request to http://localhost:8000/heartbeat?service_key=test

: curl -X POST http://localhost:8765/heartbeat?service_key=test


2 - sample service


