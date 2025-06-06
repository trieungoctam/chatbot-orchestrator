#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp for log file name
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/app_${TIMESTAMP}.log"

echo "Starting application..."
echo "Logs will be written to: ${LOG_FILE}"

# Run the application with nohup
nohup /data01/workspace/thiet/chatbot-orchestrator/venv/bin/python -m app.main > "${LOG_FILE}" 2>&1 &

# Store the PID
echo $! > logs/app.pid

echo "Application started with PID: $(cat logs/app.pid)"
echo "To view logs in real-time, use: tail -f ${LOG_FILE}"
echo "To stop the application, use: kill $(cat logs/app.pid)"

# Run UI

nohup /data01/workspace/thiet/chatbot-orchestrator/venv/bin/python -m http.server 8385 > "${LOG_FILE}" 2>&1 &