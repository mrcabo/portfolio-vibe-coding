# Investment Portfolio Tracker Docker Setup

This guide explains how to run the Investment Portfolio Tracker application using Docker, allowing you to start both the frontend and backend with a single command.

## Prerequisites

- [Docker](https://www.docker.com/get-started) installed on your machine
- [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine

## Quick Start

1. Make sure Docker is running on your system
2. Place all files in the project's root directory
3. Make the startup script executable:
   ```bash
   chmod +x start.sh
   ```
4. Run the startup script:
   ```bash
   ./start.sh
   ```

The application will now be running with:
- Frontend available at: http://localhost:3000
- Backend API available at: http://localhost:5001/api

## Manual Setup (Alternative)

If you prefer to set up the containers manually:

1. Create the two Dockerfile files (`Dockerfile.backend` and `Dockerfile.frontend`) using the content provided
2. Create the `docker-compose.yml` file using the content provided
3. Run:
   ```bash
   docker-compose up -d
   ```

## Stopping the Application

To stop the running containers:
```bash
docker-compose down
```

## Troubleshooting

If you encounter any issues:

1. Check Docker logs:
   ```bash
   docker-compose logs backend
   docker-compose logs frontend
   ```

2. Ensure the required ports (3000 and 5001) are not in use by other applications

3. Try rebuilding the containers:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Data Persistence

The application uses a `portfolio.json` file to store your portfolio data. This file is mounted as a volume in the Docker setup, so your data will persist between container restarts.

## Project Structure

Your project directory should look like this:
```
investment-tracker/
├── backend/
│   ├── app.py
│   ├── alpha_vantage_api.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── ...
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── portfolio.json
├── start.sh
└── README.md
```