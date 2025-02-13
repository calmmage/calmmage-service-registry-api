# Service Registry Todo

- [x] add service name. By default - 'service-key' -> 'Service Key'
- [ ] bonus: generate service groups with LLM
- [x] add API endpoint to toggle alerts for a service
- [x] add bot command to toggle alerts for a service (/toggle_alerts service-key)
- [x] add command to view service state transition history (/history service-key [limit])

## New Features
- [ ] Add command to set service group (/set_service_group service-key group-name)
- [ ] Add command to list all service groups (/list_groups)
- [ ] Add command to show services in a specific group (/group_status group-name)
- [ ] Add command to filter history by state type (/history service-key --state down,dead)
- [ ] Add command to show history for all services in a group (/group_history group-name) 