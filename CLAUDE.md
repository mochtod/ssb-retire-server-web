# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a VM Retirement Scheduler Web Application that provides a web interface for scheduling automated virtual machine shutdowns and retirements through Ansible Automation Platform (AAP) integration.

## Common Development Commands

### Running the Application
```bash
# Local development (runs on port 5000 with debug mode)
python app.py

# Docker deployment
docker-compose up

# Build Docker image
docker build -t ssb-retire-server-web .
```

### Testing
```bash
# Run the AAP integration test
python tests/launch_aap_job.py
```

Note: No formal test framework is currently in use. The test file directly calls the AAP API with test data.

## Architecture Overview

### Technology Stack
- **Backend**: Flask 2.3.2 (Python web framework)
- **Frontend**: Bootstrap 5.3.0, Flatpickr (date picker), Font Awesome (icons)
- **Containerization**: Docker with Gunicorn WSGI server
- **Authentication**: Basic HTTP authentication

### Key Components

1. **app.py**: Main Flask application
   - Handles web routes and AAP API integration
   - Environment-based configuration
   - Basic auth implementation
   - SSL verification disabled for internal servers

2. **Frontend (templates/index.html, static/js/script.js)**:
   - Single-page application with form validation
   - Dark/light theme toggle with localStorage persistence
   - Date/time recommendations for quick selection
   - Progress indicators during job submission

3. **AAP Integration**:
   - Launches jobs via AAP REST API
   - Uses Bearer token authentication
   - Template ID 66 configured for VM retirement jobs
   - Enforces single VM per job limitation

### Environment Variables
Required for deployment:
- `AAP_URL`: Ansible AAP server URL
- `AAP_TOKEN`: Bearer token for AAP authentication
- `AAP_TEMPLATE_ID`: Job template ID (default: 66)
- `BASIC_AUTH_USERNAME`: Web interface username
- `BASIC_AUTH_PASSWORD`: Web interface password

### Important Constraints
- **Up to 5 VMs per job**: The application allows scheduling 1-5 VMs per job
- **Internal use only**: SSL verification is disabled, indicating this is for internal corporate networks
- **No linting/formatting**: Project lacks automated code quality tools