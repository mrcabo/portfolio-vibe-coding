#!/bin/bash

# Create the Dockerfile for backend
cat > Dockerfile.backend << 'EOL'
FROM python:3.10-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY backend/ .

# Expose the port the app runs on
EXPOSE 5001

# Command to run the app
CMD ["python", "app.py"]
EOL

# Create the Dockerfile for frontend
cat > Dockerfile.frontend << 'EOL'
FROM node:18-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the frontend code
COPY frontend/ ./

# Build the application
RUN npm run build

# Install serve to run the production build
RUN npm install -g serve

# Expose the port the app runs on
EXPOSE 3000

# Command to run the app
CMD ["serve", "-s", "build", "-l", "3000"]
EOL

# Create docker-compose.yml
cat > docker-compose.yml << 'EOL'
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "5001:5001"
    volumes:
      - ./backend:/app
      - ./portfolio.json:/app/portfolio.json
    environment:
      - FLASK_ENV=development
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - REACT_APP_API_URL=http://localhost:5001/api
    restart: unless-stopped
EOL

# Make sure portfolio.json exists
if [ ! -f portfolio.json ]; then
    echo "[]" > portfolio.json
    echo "Created empty portfolio.json file"
fi

# Start the containers
echo "Starting Investment Portfolio Tracker..."
docker-compose up -d

echo ""
echo "Investment Portfolio Tracker is now running!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:5001/api"
echo ""
echo "To stop the application, run: docker-compose down"