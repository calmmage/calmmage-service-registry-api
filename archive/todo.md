# Service Registry Implementation Tasks

1. Set up project structure and dependencies
   - Create requirements.txt
   - Create example.env and .env files
   - Set up MongoDB connection utilities

2. Implement FastAPI heartbeat endpoint
   - Create service models using pydantic
   - Implement /heartbeat endpoint
   - Add MongoDB service operations

3. Enhance Telegram bot with status command
   - Add /status command implementation
   - Implement service status calculation logic
   - Add median heartbeat interval calculation
   - Add state determination logic (ok/down/dead)

4. Add tests
   - Add pytest fixtures for MongoDB
   - Add API endpoint tests
   - Add service status calculation tests

5. Documentation
   - Add README.md with setup instructions
   - Add API documentation
   - Add deployment instructions 