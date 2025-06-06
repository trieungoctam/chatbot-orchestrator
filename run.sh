#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp for log file name
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
APP_LOG_FILE="logs/app_${TIMESTAMP}.log"
UI_LOG_FILE="logs/ui_${TIMESTAMP}.log"

echo "Starting application..."
echo "App logs will be written to: ${APP_LOG_FILE}"
echo "UI logs will be written to: ${UI_LOG_FILE}"

# Run the main application with nohup
nohup /data01/workspace/thiet/chatbot-orchestrator/venv/bin/python -m app.main > "${APP_LOG_FILE}" 2>&1 &

# Store the main app PID
echo $! > logs/app.pid
echo "Main application started with PID: $(cat logs/app.pid)"

# Run UI server
nohup /data01/workspace/thiet/chatbot-orchestrator/venv/bin/python -m http.server 8385 > "${UI_LOG_FILE}" 2>&1 &

# Store the UI server PID
echo $! > logs/ui.pid
echo "UI server started with PID: $(cat logs/ui.pid)"

echo "To view app logs in real-time, use: tail -f ${APP_LOG_FILE}"
echo "To view UI logs in real-time, use: tail -f ${UI_LOG_FILE}"
echo "To stop the application, use: kill $(cat logs/app.pid) $(cat logs/ui.pid)"