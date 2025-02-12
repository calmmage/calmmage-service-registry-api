What am I doing with this?

1) just a /heartbeat (service_key) handle 
2) -> write to db

3) a sample service that can call this api to register itself every 5 minutes

4) api handle to get status of all services

5) telegram command to get status of all services

-> calls the api by the specified url of this service

## Workalong

1 - heartbeat handle.
Seems to be there.

Test manually? how? CURL POST request to http://localhost:8000/heartbeat?service_key=test

: curl -X POST http://localhost:8765/heartbeat?service_key=test


2 - sample service


