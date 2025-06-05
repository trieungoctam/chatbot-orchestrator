# Monitoring Stack

This directory contains the configuration files for the monitoring stack, which includes:
- **Loki**: for log aggregation and storage
- **Promtail**: for log collection and forwarding to Loki
- **Grafana**: for visualization and dashboards

## Getting Started

1. Start the monitoring stack:
   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

2. Access Grafana:
   - URL: http://localhost:3000
   - Username: admin
   - Password: admin

## Testing the Logging

We've included a test script to generate sample logs:

```bash
# Generate test logs
python monitoring/test_logging.py

# View the generated logs
cat logs/test.log

# Generate logs with the API server
python -m app.main

# Make API requests to generate logs
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/bots -H "X-API-KEY: dev-api-key"
```

## Log Query Syntax

In Grafana, you can use LogQL to query logs. Some examples:

1. Query all logs:
   ```
   {job="chatbot_logs"}
   ```

2. Query logs by level:
   ```
   {job="chatbot_logs", level="ERROR"}
   ```

3. Query logs containing a specific term:
   ```
   {job="chatbot_logs"} |= "API key"
   ```

4. Filter by module name:
   ```
   {job="chatbot_logs", name="app.services.ai_router"}
   ```

## Creating Dashboards

You can create custom dashboards in Grafana to visualize your log data:

1. Go to Dashboards > New Dashboard
2. Add a new panel
3. Select Loki as the data source
4. Configure your query

## Useful Panels for Chat Orchestrator

1. **Error Rate Panel**:
   ```
   count_over_time({job="chatbot_logs", level="ERROR"}[5m])
   ```

2. **API Requests Panel**:
   ```
   count_over_time({job="chatbot_logs", name="app.api"}[5m])
   ```

3. **AI Backend Requests Panel**:
   ```
   count_over_time({job="chatbot_logs", name="app.services.ai_router"}[5m])
   ```

## Troubleshooting

If you encounter issues with log collection:

1. Check if Promtail is running:
   ```bash
   docker-compose -f docker-compose.monitoring.yml ps promtail
   ```

2. Check Promtail logs:
   ```bash
   docker-compose -f docker-compose.monitoring.yml logs promtail
   ```

3. Ensure your application is writing logs to the correct directory:
   ```bash
   ls -la logs/
   ```

4. Make sure log format matches what Promtail is configured to parse:
   ```bash
   head -n 5 logs/app.log
   ```