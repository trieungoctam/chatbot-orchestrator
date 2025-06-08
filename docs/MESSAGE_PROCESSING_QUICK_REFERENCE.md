# Message Processing - Quick Reference

## 🚀 Luồng Chính

```
Request → History Processing → Lock Check → Background Job → AI Processing → Platform Action
```

## 🔑 Các Lệnh Debug Nhanh

```bash
# Check system health
curl http://localhost:8000/api/v1/chat/handler/status

# Check job status
curl http://localhost:8000/api/v1/chat/job/{job_id}/status

# Check conversation lock
curl http://localhost:8000/api/v1/chat/conversation/{conversation_id}/lock

# Force unlock conversation
curl -X DELETE http://localhost:8000/api/v1/chat/conversation/{conversation_id}/lock

# Cancel a job
curl -X DELETE http://localhost:8000/api/v1/chat/job/{job_id}
```

## 📊 Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| `MessageHandler` | Main orchestrator | `app/services/message_handler.py:1134` |
| `MessageLockManager` | Distributed locks | `app/services/message_handler.py:285` |
| `BackgroundJobManager` | Async job processing | `app/services/message_handler.py:437` |
| `HistoryProcessor` | History parsing | `app/services/message_handler.py:920` |
| `CacheManager` | Redis + Memory cache | `app/services/message_handler.py:223` |

## 🔒 Lock States

- **No Lock**: Conversation có thể process message mới
- **Lock Exists**: Conversation đang được process, messages sẽ được consolidate
- **Lock Expired**: Auto cleanup sau 1 hour

## 📝 Message Format

**Input (HTML)**:
```html
<USER>Hello</USER><br><BOT>Hi there!</BOT><br>
```

**Output (JSON)**:
```json
[
  {"role": "user", "content": "Hello", "timestamp": 1704067200},
  {"role": "assistant", "content": "Hi there!", "timestamp": 1704067201}
]
```

## ⚡ Performance Settings

```python
# Constants trong message_handler.py
LOCK_TTL_SECONDS = 3600        # Lock timeout
JOB_TTL_SECONDS = 3600         # Job cache timeout
CACHE_TTL_SECONDS = 3600       # History cache timeout
WORKER_TIMEOUT_SECONDS = 10    # Worker polling timeout
CLEANUP_MAX_AGE_HOURS = 24     # Auto cleanup interval
```

## 🚨 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Background worker not running" | Worker crashed | Auto-restart implemented |
| High lock contention | Multiple rapid requests | Consolidation mechanism |
| Memory growth | Cache not clearing | TTL + periodic cleanup |
| Slow responses | Database bottleneck | Connection pooling |

## 📋 Environment Variables

```bash
LOG_LEVEL=WARNING          # Reduce log noise
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
```

## 🔧 Essential APIs

**Send Message**:
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "uuid",
    "bot_id": "uuid",
    "history": "<USER>Hello</USER><br>"
  }'
```

**Response**:
```json
{
  "success": true,
  "status": "ai_processing_started",
  "ai_job_id": "1704067200.123",
  "lock_id": 1704067200123,
  "message": "Message received and AI processing started"
}
```