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