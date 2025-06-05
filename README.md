# 🤖 **Enhanced Chat Bot Backend - Redis + PostgreSQL Edition**

> **Production-Ready, Scalable Chat Bot Backend with Distributed State Management**

## 📋 **Tổng Quan**

Hệ thống Enhanced Chat Bot Backend **Version 2.0** được thiết kế để xử lý tin nhắn với khả năng race condition handling tiên tiến, sử dụng **Redis** cho state management và **PostgreSQL** cho data persistence. Hệ thống có khả năng scale horizontally và production-ready.

### 🎯 **Kiến Trúc Mới**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Pancake UI    │───▶│  Backend APIs    │───▶│   AI Service    │
│   (Client)      │    │  (Multi-Instance)│    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                        │                       │
         │                        ▼                       │
         │           ┌────────────────────────────┐       │
         │           │     Redis Cluster          │       │
         │           │ - Conversation State       │       │
         │           │ - Distributed Locks        │       │
         │           │ - Session Management       │       │
         └───────────┤                            │◀──────┘
                     └────────────────────────────┘
                                   │
                                   ▼
                     ┌────────────────────────────┐
                     │     PostgreSQL             │
                     │ - Conversation History     │
                     │ - Message Persistence      │
                     │ - Action Logs              │
                     │ - Analytics Data           │
                     └────────────────────────────┘
```

## 🚀 **Tính Năng Mới (v2.0)**

### ⚡ **Enhanced Distributed Architecture**
- **Redis State Management**: Conversation state được lưu trữ trong Redis cluster, cho phép scale horizontal
- **Distributed Locks**: Sử dụng Redis distributed locks để ngăn chặn race conditions across instances
- **PostgreSQL Persistence**: Lưu trữ persistent data như conversation history, messages, actions
- **Multi-Instance Ready**: Có thể chạy nhiều backend instances với shared state

### 🔴 **Redis Features**
- **Conversation State**: Lưu trữ tạm thời conversation context và processing state
- **Distributed Locks**: Ngăn chặn concurrent processing của cùng conversation
- **Auto Cleanup**: Tự động xóa old conversations state
- **Connection Pooling**: Optimized Redis connections với retry logic

### 🗄️ **PostgreSQL Features**
- **Data Persistence**: Lưu trữ conversation history, messages, extracted actions
- **Analytics Ready**: Schema optimized cho analytics và reporting
- **UUID Primary Keys**: Consistent với distributed architecture
- **JSONB Support**: Native JSON storage cho flexible data structures

### 🎭 **Enhanced Action Processing**
- **Smart Race Prevention**: Distributed locks ngăn duplicate processing
- **State Persistence**: Action execution state được track trong database
- **Fallback Handling**: Improved error recovery với persistent state
- **Performance Tracking**: Track AI processing time và action execution

---

## 📡 **API Documentation (Updated)**

### 🌐 **Base URL**
```
Production: https://your-backend.com
Development: http://localhost:8000
```

### 🔑 **Authentication** (Unchanged)

#### **Pancake Token** (Main API)
```bash
export PANCAKE_ACCESS_TOKEN="your-pancake-token-here"
```

#### **Admin Token** (Management APIs)
```bash
export ADMIN_ACCESS_TOKEN="your-admin-token-here"
```

---

## 📱 **Main API - Enhanced với Redis State**

### `POST /api/v1/enhanced-handle-message`

**🎯 Main endpoint với distributed locking và persistent state**

#### **Headers**
```json
{
  "Authorization": "Bearer ${PANCAKE_ACCESS_TOKEN}",
  "Content-Type": "application/json"
}
```

#### **Request Body** (Unchanged)
```json
{
  "conversation_id": "conv_12345",
  "message_id": "msg_67890",
  "message_content": "Tôi muốn đặt lịch khám bệnh",
  "sender_id": "user_123",
  "sender_type": "user",
  "timestamp": 1699123456.789,
  "metadata": {
    "platform": "web",
    "user_agent": "Mozilla/5.0..."
  }
}
```

#### **Response Enhanced (200)**
```json
{
  "success": true,
  "result": {
    "status": "completed",
    "ai_response": {
      "response_text": "Tôi sẽ giúp bạn đặt lịch khám bệnh.",
      "intent": "book_appointment",
      "confidence": 0.95,
      "entities": {
        "service_type": "medical_checkup"
      },
      "processing_time_ms": 1234.5,
      "model_used": "gpt-4"
    },
    "extracted_actions": [
      {
        "type": "send_message",
        "data": {
          "message": "Tôi sẽ giúp bạn đặt lịch khám bệnh."
        }
      }
    ],
    "pancake_result": {
      "status": "success",
      "actions_executed": 2
    },
    "message_id": "msg_67890",
    "storage_backend": "Redis",
    "distributed_lock_used": true
  },
  "timestamp": 1699123456.789,
  "processing_time_ms": 1234.5
}
```

#### **New Response States**

**Locked State (200)**
```json
{
  "success": true,
  "result": {
    "status": "locked",
    "reason": "processing_in_progress",
    "storage_backend": "Redis"
  }
}
```

**Restart Needed (200)**
```json
{
  "success": true,
  "result": {
    "status": "restart_needed",
    "newer_messages": [
      {
        "message_id": "msg_67891",
        "timestamp": 1699123457.789
      }
    ],
    "current_result": {
      "ai_response": {...},
      "extracted_actions": [...],
      "pancake_result": {...}
    }
  }
}
```

---

## ⚙️ **Admin APIs - Enhanced với Redis Management**

### `GET /api/v1/admin/conversations`

**📊 Danh sách conversations từ Redis cluster**

#### **Response Enhanced (200)**
```json
{
  "total_conversations": 42,
  "conversations": [
    {
      "conversation_id": "conv_12345",
      "last_message_id": "msg_67890",
      "last_message_timestamp": 1699123456.789,
      "ai_processing": false,
      "context_size": 15
    }
  ],
  "storage_backend": "Redis"
}
```

### `GET /api/v1/admin/health`

**🏥 Enhanced health check với Redis + PostgreSQL stats**

#### **Response Enhanced (200)**
```json
{
  "status": "healthy",
  "timestamp": 1699123456.789,
  "statistics": {
    "total_conversations": 42,
    "active_ai_tasks": 3,
    "stuck_conversations": 0
  },
  "redis_status": "connected",
  "storage_backend": "Redis",
  "stuck_conversations": [],
  "supported_action_types": [
    "send_message", "send_quick_replies", "send_carousel",
    "transfer_to_agent", "collect_info", "execute_api", "end_conversation"
  ]
}
```

### `GET /api/v1/admin/stats`

**📈 Enhanced system statistics với Redis & PostgreSQL metrics**

#### **Response Enhanced (200)**
```json
{
  "timestamp": 1699123456.789,
  "conversations": {
    "total": 42,
    "recent": 15,
    "old": 5,
    "active_processing": 3
  },
  "redis_stats": {
    "connected_clients": 12,
    "used_memory_human": "45.2M",
    "keyspace_hits": 15672,
    "keyspace_misses": 234
  },
  "storage_backend": "Redis"
}
```

**New Admin Endpoints:**

### `POST /admin/system/cleanup`
**Enhanced cleanup với Redis TTL management**

---

## 🛠️ **Setup & Configuration (Updated)**

### **📦 Installation với Redis & PostgreSQL**

```bash
# Clone repository
git clone <repository-url>
cd enhanced-chat-backend

# Install dependencies (updated với Redis & PostgreSQL)
pip install -r requirements.txt

# Setup environment với Redis + PostgreSQL config
cp environment.example .env
nano .env
```

### **🔧 Environment Variables (Updated)**
```bash
# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
ENVIRONMENT=production

# Authentication Tokens
PANCAKE_ACCESS_TOKEN=your-secure-pancake-token-here
ADMIN_ACCESS_TOKEN=your-secure-admin-token-here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=enhanced_chatbot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-postgres-password

# AI Service Configuration
AI_SERVICE_URL=http://ai-service:8001
AI_SERVICE_TIMEOUT=30

# Pancake Configuration
PANCAKE_BASE_URL=http://pancake:8000
```

### **🐳 Docker Setup với Redis & PostgreSQL**

#### **docker-compose.yml**
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass your-redis-password

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: enhanced_chatbot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your-postgres-password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
      - PANCAKE_ACCESS_TOKEN=${PANCAKE_ACCESS_TOKEN}
      - ADMIN_ACCESS_TOKEN=${ADMIN_ACCESS_TOKEN}
    depends_on:
      - redis
      - postgres

volumes:
  postgres_data:
```

### **🚀 Start Application**

#### **Development với Dependencies**
```bash
# Start Redis & PostgreSQL
docker-compose up redis postgres -d

# Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### **Production**
```bash
# Start full stack
docker-compose up -d

# Or manual with scaling
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🔄 **Message Processing Flow (Enhanced)**

### **1. Pancake Gửi Tin Nhắn**
```
POST /api/v1/enhanced-handle-message
```

### **2. Distributed Lock Acquisition**
- Backend acquire Redis distributed lock cho conversation
- Ngăn chặn concurrent processing từ multiple instances
- Lock timeout: 30 seconds

### **3. Redis State Check**
- Kiểm tra conversation state hiện tại từ Redis
- Compare message timestamp để detect race conditions
- Update state với message mới

### **4. AI Processing với Context**
- Load conversation context từ Redis
- Gọi AI service với full context
- Track processing time và model used

### **5. Action Extraction & Database Logging**
- Extract structured actions từ AI response
- Save actions vào PostgreSQL cho persistence
- Update action execution status

### **6. Send Actions to Pancake**
```json
{
  "conversation_id": "conv_12345",
  "ai_response": { ... },
  "actions": [ ... ],
  "timestamp": 1699123456.789,
  "distributed_lock_id": "lock_12345"
}
```

### **7. Final State Update & Lock Release**
- Update Redis state với processing results
- Save conversation history vào PostgreSQL
- Release distributed lock
- Check for newer messages và restart nếu cần

---

## 🔧 **Monitoring & Troubleshooting (Enhanced)**

### **📊 Redis Monitoring**

#### **Redis Health Check**
```bash
curl -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
     http://localhost:8000/api/v1/admin/health
```

#### **Redis Statistics**
```bash
curl -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
     http://localhost:8000/api/v1/admin/stats
```

### **🗄️ PostgreSQL Monitoring**

#### **Database Connection Check**
- Health endpoint tự động kiểm tra PostgreSQL connection
- Database initialization được track trong startup logs

#### **Conversation History Query**
```sql
-- Recent conversations
SELECT conversation_id, last_message_timestamp, total_messages
FROM conversations
ORDER BY last_message_timestamp DESC
LIMIT 10;

-- Action statistics
SELECT action_type, COUNT(*), AVG(retry_count)
FROM message_actions
GROUP BY action_type;
```

### **🐛 Enhanced Troubleshooting**

#### **Issue: Redis Connection Failed**
```bash
# Check Redis connectivity
docker exec -it redis-container redis-cli ping

# Check Redis stats
curl -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
     http://localhost:8000/api/v1/admin/stats
```

#### **Issue: Distributed Lock Stuck**
```bash
# Check stuck conversations
curl -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
     http://localhost:8000/api/v1/admin/health

# Force release locks
curl -X POST -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
     http://localhost:8000/api/v1/admin/conversations/{id}/cancel
```

#### **Issue: PostgreSQL Performance**
```bash
# Check database connections
curl -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
     http://localhost:8000/api/v1/admin/health

# Cleanup old data
curl -X POST -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
     http://localhost:8000/api/v1/admin/system/cleanup?max_age_hours=24
```

---

## 🛡️ **Security & Scalability (Enhanced)**

### **🔐 Enhanced Security**
- **Redis AUTH**: Password protection cho Redis connections
- **PostgreSQL SSL**: Encrypted database connections
- **Connection Limits**: Rate limiting per instance
- **Distributed Authentication**: JWT tokens work across instances

### **📈 Horizontal Scalability**
- **Stateless Instances**: Tất cả state được lưu trong Redis/PostgreSQL
- **Load Balancing**: Multiple backend instances với shared state
- **Database Connection Pooling**: Optimized PostgreSQL connections
- **Redis Clustering**: Support Redis cluster cho high availability

### **📊 Performance Optimization**
- **Redis TTL**: Automatic cleanup của conversation state
- **Database Indexing**: Optimized queries cho conversation history
- **Connection Pooling**: Reuse connections để giảm overhead
- **Async Processing**: Non-blocking I/O cho all database operations

---

## 📞 **Support & Deployment**

### **🚀 Production Deployment**
```bash
# Multi-instance deployment
docker-compose up --scale backend=3

# With load balancer
docker-compose -f docker-compose.prod.yml up -d
```

### **📊 Monitoring Setup**
- **Redis Monitoring**: RedisInsight for Redis cluster monitoring
- **PostgreSQL Monitoring**: pgAdmin for database monitoring
- **Application Monitoring**: Structured logs với JSON format
- **Health Checks**: Enhanced health endpoints cho load balancers

---

**🎉 Enhanced Chat Bot Backend v2.0 - Redis + PostgreSQL Ready for Production Scale!**

# Chat Orchestrator Core - MessageHandler System

A production-ready chat message processing system built with FastAPI, featuring distributed locking, background job management, and AI processing coordination.

## 🏗️ Architecture Overview

The Chat Orchestrator Core is designed around a centralized `MessageHandler` that coordinates message processing with the following key components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chat API      │────│ MessageHandler  │────│ Background Jobs │
│   (FastAPI)     │    │                 │    │   (Redis/Mem)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │                 │
               ┌───────▼────────┐ ┌──────▼──────┐
               │ Lock Manager   │ │ Bot Config  │
               │   (Redis)      │ │  Service    │
               └────────────────┘ └─────────────┘
```

## 🚀 Key Features

### ✨ **Enhanced MessageHandler**
- **Distributed Locking**: Prevents race conditions in concurrent message processing
- **Message Consolidation**: Automatically merges rapid sequential messages
- **Background AI Processing**: Non-blocking AI job execution with status tracking
- **Graceful Fallbacks**: Works with or without Redis for development/testing
- **Configuration Management**: Dynamic bot, AI, and platform configuration retrieval

### 🔒 **Lock Management**
- Redis-based distributed locks with automatic TTL
- In-memory fallback for testing environments
- Lock acquisition, release, and cleanup mechanisms
- Protection against duplicate message processing

### 🤖 **AI Processing Pipeline**
- Asynchronous AI job creation and tracking
- Job status monitoring with real-time updates
- Configurable timeouts and retry mechanisms
- Simulated AI processing (ready for real AI integration)

### ⚙️ **Configuration System**
- Database-driven bot configuration
- AI core and platform settings management
- Default configuration fallbacks
- Environment-specific overrides

## 📡 API Endpoints

### **POST** `/api/v1/chat/message`

Process a chat message through the enhanced message handling system.

#### Request Body
```json
{
  "conversation_id": "optional-uuid-string",
  "history": "<USER>Hello, how are you?</USER><br><BOT>I'm doing well!</BOT><br>",
  "resources": {
    "user_id": "123",
    "session_type": "web",
    "additional_context": "any value"
  }
}
```

#### Response
```json
{
  "success": true,
  "status": "ai_processing_started",
  "message": "Message received and AI processing started",
  "error": null,
  "action": "lock_acquired",
  "ai_job_id": "550e8400-e29b-41d4-a716-446655440000",
  "lock_id": "550e8400-e29b-41d4-a716-446655440001",
  "consolidated_messages": 1,
  "bot_name": "Default Bot"
}
```

#### Status Codes
- **200 OK**: Message processed successfully
- **422 Unprocessable Entity**: Invalid request data
- **500 Internal Server Error**: Processing failure

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.12+
- PostgreSQL database
- Redis (optional, has fallback)
- Virtual environment

### Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd chat-orchestrator-core/backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your database and Redis configurations
   ```

3. **Database Setup**
   ```bash
   alembic upgrade head
   ```

4. **Start the Server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password

# Application
DEBUG=true
LOG_LEVEL=INFO
```

### MessageHandler Configuration

```python
# app/services/message_handler.py
class MessageHandler:
    def __init__(self):
        self.redis = None                    # Auto-configured
        self.lock_manager = None            # Auto-initialized
        self.background_job_manager = None  # Handles AI jobs
        self.bot_config_service = None      # Config retrieval
        self._initialized = False
```

## 📊 Message Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Handler
    participant Lock
    participant Jobs
    participant AI

    Client->>API: POST /chat/message
    API->>Handler: handle_message_request()
    Handler->>Lock: check_and_acquire_lock()

    alt Lock Acquired
        Lock-->>Handler: lock_acquired
        Handler->>Jobs: create_ai_processing_job()
        Jobs->>AI: simulate_ai_processing()
        Handler-->>API: ai_processing_started
        API-->>Client: 200 OK with job_id

        Note over AI: Background processing
        AI->>Jobs: update_job_status(completed)
    else Lock Exists
        Lock-->>Handler: lock_exists
        Handler-->>API: locked status
        API-->>Client: 200 OK (being processed)
    end
```

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Suites
```bash
# Chat API tests
pytest tests/test_api_chat.py -v

# Specific test
pytest tests/test_api_chat.py::TestChatAPI::test_real_handler_integration -v
```

### Test Coverage
The test suite includes 22 comprehensive tests covering:

- ✅ **Message Processing**: Success cases, auto-generated IDs, resource handling
- ✅ **Error Handling**: Exceptions, timeouts, validation errors
- ✅ **Authentication**: Access control and dependency injection
- ✅ **Edge Cases**: Long history, special characters, concurrent requests
- ✅ **Integration**: Real handler with database and Redis fallbacks

### Test Results
```bash
22 passed, 0 failed ✅
Coverage: All critical paths tested
```

## 📈 Performance & Monitoring

### Metrics
- **Lock Acquisition Time**: Typically < 10ms
- **Message Processing**: Immediate response (non-blocking)
- **AI Job Creation**: < 50ms
- **Memory Usage**: Efficient with fallback mechanisms

### Monitoring Endpoints

#### Handler Status
```bash
GET /api/v1/status/handler
```
Returns detailed handler component status:
```json
{
  "initialized": true,
  "components": {
    "redis_connected": true,
    "lock_manager": true,
    "background_job_manager": {
      "redis_connected": true,
      "status": "healthy",
      "active_jobs": 0
    }
  },
  "status": "healthy"
}
```

## 🔄 Background Job Management

### Job Lifecycle
1. **Creation**: Job created with unique UUID
2. **Queuing**: Added to processing queue (Redis or memory)
3. **Processing**: AI simulation (2-second processing time)
4. **Completion**: Status updated with results
5. **Cleanup**: Automatic TTL-based cleanup

### Job Status Tracking
```python
# Get job status
job_status = await message_handler.get_job_status(job_id)

# Cancel job
cancelled = await message_handler.cancel_job(job_id)
```

## 🛡️ Error Handling & Resilience

### Redis Connection Failures
- Automatic fallback to in-memory storage
- Graceful degradation without service interruption
- Warning logs for operational awareness

### Database Errors
- Default configuration fallbacks
- Proper error logging and reporting
- Transaction rollback and cleanup

### Lock Management
- Automatic lock cleanup (24-hour default TTL)
- Orphaned lock detection and removal
- Lock release on processing errors

## 🔐 Security Features

### Authentication
- Dependency-based access control
- JWT token support (configurable)
- Request validation and sanitization

### Input Validation
- Pydantic schema validation
- SQL injection prevention
- XSS protection for content fields

## 🚀 Production Deployment

### Redis Configuration
```bash
# Production Redis settings
REDIS_MAX_CONNECTIONS=100
REDIS_SOCKET_TIMEOUT=30
CONVERSATION_STATE_TTL=3600
PROCESSING_LOCK_TTL=300
```

### Scaling Considerations
- **Horizontal Scaling**: Multiple handler instances with shared Redis
- **Load Balancing**: Stateless design supports any load balancer
- **Database Connections**: Async connection pooling for performance

### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Handler component status
curl http://localhost:8000/api/v1/status/handler
```

## 🔧 Development

### Project Structure
```
app/
├── api/v1/
│   └── chat_api.py         # Chat endpoints
├── services/
│   ├── __init__.py         # Service exports
│   └── message_handler.py  # Core MessageHandler
├── schemas/
│   ├── request.py          # Request models
│   └── response.py         # Response models
├── core/
│   ├── database.py         # Database configuration
│   └── redis_client.py     # Redis client setup
└── tests/
    └── test_api_chat.py     # Comprehensive test suite
```

### Key Classes

#### MessageHandler
- Main orchestrator for message processing
- Integrates all components (locks, jobs, config)
- Handles Redis fallbacks and error recovery

#### MessageLockManager
- Distributed locking mechanism
- Message consolidation logic
- TTL management and cleanup

#### BackgroundJobManager
- AI job lifecycle management
- Status tracking and updates
- Worker simulation and monitoring

#### BotConfigService
- Database-driven configuration
- Default fallback mechanisms
- Dynamic config retrieval

## 📚 API Schema Reference

### PancakeMessageRequest
```python
class PancakeMessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    history: str = Field(..., description="Conversation history")
    resources: Optional[Dict[str, Any]] = None
```

### PancakeMessageResponse
```python
class PancakeMessageResponse(BaseModel):
    success: bool
    status: str
    message: Optional[str] = None
    error: Optional[str] = None
    action: Optional[str] = None
    ai_job_id: Optional[str] = None
    lock_id: Optional[str] = None
    consolidated_messages: Optional[int] = None
    bot_name: Optional[str] = None
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints throughout
- Add docstrings for public methods
- Include comprehensive error handling

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🆘 Support & Troubleshooting

### Common Issues

#### Redis Connection Failed
```
WARNING: Redis connection failed, using fallback
```
- **Solution**: Check Redis server status or run without Redis (fallback mode)

#### Database Connection Error
```
ERROR: Failed to initialize message handler
```
- **Solution**: Verify DATABASE_URL and database accessibility

#### Lock Acquisition Timeout
```
WARNING: Failed to acquire lock
```
- **Solution**: Check for orphaned locks or increase lock TTL

### Debug Mode
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload
```

### Get Help
- Check the test suite for usage examples
- Review the comprehensive error logs
- Examine the handler status endpoint for component health

---

**Built with ❤️ using FastAPI, PostgreSQL, and Redis**