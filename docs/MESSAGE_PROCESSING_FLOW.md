# Tài Liệu Xử Lý Message - Chat Orchestrator Core

## 📋 Tổng Quan

Hệ thống xử lý message được thiết kế để xử lý các cuộc hội thoại một cách an toàn, hiệu quả và có khả năng mở rộng. Sử dụng kiến trúc event-driven với background processing, distributed locks và cache management.

## 🏗️ Kiến Trúc Tổng Thể

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Request   │───▶│ MessageHandler  │───▶│ BackgroundJob   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────┐        ┌─────────────────┐
                       │ LockManager │        │   AI Service    │
                       └─────────────┘        └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────┐        ┌─────────────────┐
                       │ Redis Cache │        │ Platform Action │
                       └─────────────┘        └─────────────────┘
```

## 🔧 Các Component Chính

### 1. MessageHandler
**Nhiệm vụ**: Điều phối toàn bộ quá trình xử lý message
- Khởi tạo và quản lý các component con
- Xử lý lock và queue management
- Coordinate giữa các services

### 2. MessageLockManager
**Nhiệm vụ**: Quản lý distributed locks để tránh race conditions
- Kiểm tra và tạo lock cho conversation
- Consolidate multiple messages
- Quản lý lock lifecycle

### 3. BackgroundJobManager
**Nhiệm vụ**: Xử lý AI jobs trong background
- Queue management với worker pool
- Job status tracking
- Error handling và retry logic

### 4. HistoryProcessor
**Nhiệm vụ**: Xử lý và quản lý lịch sử hội thoại
- Parse history string thành structured messages
- Cache và cut old history
- Database persistence

### 5. CacheManager
**Nhiệm vụ**: Quản lý cache với fallback mechanism
- Redis primary + Memory fallback
- JSON serialization/deserialization
- TTL management

## 📊 Luồng Xử Lý Message

### Phase 1: Request Processing
```
1. API Request đến /api/v1/chat/message
2. Validate input (conversation_id, history, bot_id)
3. Get or create conversation trong database
4. Load configurations (bot, AI, platform)
```

### Phase 2: History Processing
```
1. Cut old history để chỉ lấy phần mới
2. Parse history string thành array of messages
3. Cache processed history
```

### Phase 3: Lock Management
```
1. Check existing lock cho conversation
2. Nếu có lock:
   - Cancel previous job
   - Consolidate messages
   - Update lock với consolidated count
3. Nếu không có lock:
   - Tạo new lock với timestamp-based ID
   - Set TTL = 1 hour
```

### Phase 4: Background Job Processing
```
1. Tạo AI processing job với payload:
   - conversation_id, messages, configs
   - lock_id, resources
2. Queue job cho background worker
3. Worker xử lý job:
   - Call AI service
   - Handle success/failure
   - Execute platform actions
```

### Phase 5: Cleanup & Platform Actions
```
1. Update job status thành "completed"
2. Save history to database
3. Remove lock
4. Execute platform actions (NOTIFY, UPDATE, etc.)
```

## 🔒 Lock Management Chi Tiết

### Lock Structure
```python
@dataclass
class LockData:
    conversation_id: str
    history_hash: int
    created_at: float
    lock_id: int  # Timestamp milliseconds
    consolidated_count: int
    ai_job_id: Optional[str]
    previous_ai_job_id: Optional[str]
```

### Lock Lifecycle
1. **Creation**: Tạo khi có message mới và chưa có lock
2. **Update**: Cập nhật khi có message mới trong khi đang process
3. **Consolidation**: Merge multiple messages thành 1 job
4. **Removal**: Xóa sau khi hoàn thành hoặc lỗi

### Lock TTL
- **Default**: 1 hour (3600 seconds)
- **Auto cleanup**: Chạy định kỳ để xóa old locks
- **Force release**: API endpoint để force unlock

## 🚀 Background Job Processing

### Worker Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Job Creator    │───▶│  Queue (Redis)  │───▶│ Worker Process  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │   AI Service    │
                                               └─────────────────┘
```

### Job Status Flow
```
PENDING → PROCESSING → COMPLETED
                    └─► FAILED
                    └─► CANCELLED
```

### Self-Healing Mechanism
```python
# Auto-restart worker if not running
if not self._worker_running:
    logger.warning("Background worker not running, attempting to start it")
    await self.start_background_worker()
    if self._worker_running:
        await self._processing_queue.put(job_id)
    else:
        # Fallback to immediate processing
        asyncio.create_task(self._process_ai_job(job_id))
```

## 📚 History Management

### History Format
Input:
```html
<USER>Xin chào</USER><br>
<BOT>Chào bạn!</BOT><br>
<USER>Tôi cần hỗ trợ</USER><br>
```

Output:
```python
[
    {"role": "user", "content": "Xin chào", "timestamp": 1704067200},
    {"role": "assistant", "content": "Chào bạn!", "timestamp": 1704067201},
    {"role": "user", "content": "Tôi cần hỗ trợ", "timestamp": 1704067202}
]
```

### History Processing Steps
1. **Cut Old History**: Lấy chỉ phần mới so với cached history
2. **Parse**: Chuyển từ HTML format sang structured messages
3. **Validate**: Kiểm tra format và content
4. **Cache**: Lưu vào Redis với TTL
5. **Persist**: Lưu vào database sau khi AI process thành công

## 🔧 Platform Actions

### Supported Actions
- **NOTIFY**: Gửi thông báo tới platform
- **UPDATE**: Cập nhật conversation status
- **OUT_OF_SCOPE**: Chuyển thành NOTIFY

### Action Execution Flow
```
1. AI processing complete → AI returns action
2. Save history to database (BEFORE platform actions)
3. Remove lock (BEFORE platform actions)
4. Execute platform action
5. Update job status to completed
```

### Platform Action Payload
```python
{
    "conversation_id": "uuid",
    "ai_response": {...},
    "action_type": "NOTIFY",
    "metadata": {...}
}
```

## ⚙️ Configuration Management

### Bot Configuration
```python
{
    "bot_id": "uuid",
    "name": "Customer Support Bot",
    "language": "vi",
    "core_ai_id": "uuid",
    "platform_id": "uuid"
}
```

### AI Configuration
```python
{
    "core_ai_id": "uuid",
    "api_endpoint": "https://ai-service.com/api",
    "timeout_seconds": 30,
    "auth_token": "bearer-token"
}
```

### Platform Configuration
```python
{
    "platform_id": "uuid",
    "base_url": "https://platform.com/api",
    "actions": [
        {"name": "NOTIFY", "path": "/notify", "method": "POST"}
    ]
}
```

## 🛡️ Error Handling

### AI Processing Errors
- **Timeout**: Retry với exponential backoff
- **Service Unavailable**: Fallback mechanism
- **Invalid Response**: Log error và return default response

### Lock Errors
- **Lock Conflict**: Queue job khi lock release
- **Lock Timeout**: Force release và retry
- **Redis Unavailable**: Fallback to memory cache

### Database Errors
- **Connection Lost**: Retry với connection pool
- **Query Timeout**: Log warning và continue
- **Transaction Failed**: Rollback và retry

## 📊 Monitoring & Metrics

### Key Metrics
- **Message Processing Time**: Average time per message
- **Lock Contention**: Number of lock conflicts
- **Queue Length**: Background job queue size
- **Error Rate**: Failed jobs percentage

### Health Checks
```python
{
    "initialized": true,
    "components": {
        "cache_manager": true,
        "redis_connected": true,
        "background_job_manager": {
            "worker_running": true,
            "queue_size": 0,
            "status": "healthy"
        }
    },
    "status": "healthy"
}
```

## 🔧 API Endpoints

### Main Processing
```
POST /api/v1/chat/message
{
    "conversation_id": "uuid",
    "bot_id": "uuid",
    "history": "<USER>Hello</USER><br>",
    "resources": {}
}
```

### Management APIs
```
GET /api/v1/chat/job/{job_id}/status
DELETE /api/v1/chat/job/{job_id}
GET /api/v1/chat/conversation/{id}/lock
DELETE /api/v1/chat/conversation/{id}/lock
GET /api/v1/chat/handler/status
```

## 🚀 Performance Optimizations

### Caching Strategy
- **Redis**: Primary cache cho locks, jobs, history
- **Memory**: Fallback cache khi Redis unavailable
- **TTL**: Automatic cleanup để tránh memory leaks

### Background Processing
- **Async Workers**: Non-blocking job processing
- **Queue Management**: FIFO với priority support
- **Auto-scaling**: Worker count dựa trên queue length

### Database Optimizations
- **Connection Pooling**: Reuse connections
- **Async Operations**: Non-blocking database calls
- **Batch Operations**: Group multiple updates

## 🔍 Debugging & Troubleshooting

### Common Issues

1. **Background worker not running**
   - **Nguyên nhân**: Worker crashed hoặc chưa start
   - **Giải pháp**: Auto-restart mechanism đã implement

2. **Lock conflicts**
   - **Nguyên nhân**: Multiple requests cùng lúc
   - **Giải pháp**: Consolidation mechanism

3. **High memory usage**
   - **Nguyên nhân**: Cache không cleanup
   - **Giải pháp**: TTL và periodic cleanup

### Debug Commands
```bash
# Check handler status
curl http://localhost:8000/api/v1/chat/handler/status

# Check specific job
curl http://localhost:8000/api/v1/chat/job/{job_id}/status

# Check conversation lock
curl http://localhost:8000/api/v1/chat/conversation/{id}/lock
```

## 📈 Future Enhancements

### Planned Features
1. **Multi-tenant Support**: Isolate conversations by tenant
2. **Advanced Retry Logic**: Exponential backoff với jitter
3. **Metrics Dashboard**: Real-time monitoring
4. **Auto-scaling**: Dynamic worker management
5. **Circuit Breaker**: Prevent cascade failures

### Performance Improvements
1. **Message Batching**: Process multiple messages together
2. **Streaming Responses**: Real-time response streaming
3. **Edge Caching**: CDN integration
4. **Database Sharding**: Horizontal scaling

---

**Tác giả**: AI Assistant
**Cập nhật lần cuối**: 2025-06-09
**Version**: 2.0.0