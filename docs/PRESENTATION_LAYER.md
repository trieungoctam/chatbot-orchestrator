# Presentation Layer - Chat Orchestrator

## 🎯 **Overview**

Presentation Layer provides the REST API interface using FastAPI, handling HTTP requests/responses and serving as the entry point for external clients.

## 🏗️ **Architecture**

```
📁 app/presentation/
├── 📁 api/                # FastAPI application
│   ├── main.py           # Application factory
│   └── 📁 routers/       # API route handlers
│       ├── bots.py       # Bot management endpoints
│       ├── conversations.py  # Conversation endpoints
│       ├── messages.py   # Message endpoints
│       └── health.py     # Health check endpoints
├── 📁 models/            # Pydantic request/response models
│   ├── bot_models.py     # Bot API models
│   ├── conversation_models.py  # Conversation API models
│   └── message_models.py # Message API models
├── 📁 middleware/        # Custom middleware
│   ├── error_handler.py  # Error handling
│   ├── request_logging.py  # Request logging
│   └── auth.py          # Authentication
└── 📁 dependencies/      # Dependency injection
    └── use_cases.py      # Use case dependencies
```

## 📝 **Components Implemented**

### **1. FastAPI Application**

#### **Application Factory**
```python
def create_app(
    title: str = "Chat Orchestrator API",
    description: str = "Chat Orchestrator Core Backend API",
    version: str = "1.0.0",
    debug: bool = False
) -> FastAPI:
    """Create configured FastAPI application"""
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan  # Async startup/shutdown
    )

    setup_middleware(app)
    setup_routers(app)
    setup_exception_handlers(app)

    return app
```

#### **Lifespan Management**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    logger.info("Database initialized")

    yield

    # Shutdown
    await close_database()
    logger.info("Database connections closed")
```

### **2. API Routers**

#### **Bot Management API**
```
POST   /api/v1/bots                 # Create bot
GET    /api/v1/bots/{bot_id}        # Get bot
PUT    /api/v1/bots/{bot_id}        # Update bot
DELETE /api/v1/bots/{bot_id}        # Delete bot
GET    /api/v1/bots                 # List bots
POST   /api/v1/bots/search          # Search bots
POST   /api/v1/bots/{bot_id}/operations  # Bot operations
GET    /api/v1/bots/{bot_id}/statistics  # Bot statistics
```

#### **Conversation Management API**
```
POST   /api/v1/conversations        # Start conversation
GET    /api/v1/conversations/{id}   # Get conversation
PUT    /api/v1/conversations/{id}   # Update conversation
POST   /api/v1/conversations/{id}/messages  # Send message
POST   /api/v1/conversations/{id}/escalate  # Escalate
POST   /api/v1/conversations/{id}/transfer  # Transfer
POST   /api/v1/conversations/{id}/end       # End conversation
GET    /api/v1/conversations        # List conversations
POST   /api/v1/conversations/search # Search conversations
```

#### **Message Management API**
```
POST   /api/v1/messages             # Create message
GET    /api/v1/messages/{id}        # Get message
PUT    /api/v1/messages/{id}        # Update message
POST   /api/v1/messages/{id}/retry  # Retry message
GET    /api/v1/messages             # List messages
POST   /api/v1/messages/search      # Search messages
POST   /api/v1/messages/bulk        # Bulk operations
GET    /api/v1/messages/analytics   # Message analytics
```

### **3. Request/Response Models**

#### **Bot Models**
```python
class CreateBotRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    bot_type: str = Field(..., regex="^(customer_service|sales|support|general)$")
    language: str = Field("en", min_length=2, max_length=10)
    core_ai_id: UUID
    platform_id: UUID
    config: BotConfigRequest

class BotResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    bot_type: str
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, dto: BotDTO) -> 'BotResponse':
        return cls(**dto.__dict__)
```

#### **API Response Format**
```python
# Success Response
{
    "data": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Customer Service Bot",
        "status": "active"
    },
    "metadata": {
        "timestamp": "2024-01-01T12:00:00Z",
        "request_id": "req_123"
    }
}

# Error Response
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data",
        "details": {
            "field": "name",
            "value": "",
            "reason": "Name cannot be empty"
        }
    },
    "metadata": {
        "timestamp": "2024-01-01T12:00:00Z",
        "request_id": "req_123"
    }
}
```

### **4. Middleware**

#### **Error Handling Middleware**
```python
class ErrorHandlerMiddleware:
    async def __call__(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ApplicationError as e:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details
                    }
                }
            )
```

#### **Request Logging Middleware**
```python
class RequestLoggingMiddleware:
    async def __call__(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        logger.info("Request started",
                   method=request.method,
                   path=request.url.path,
                   client_ip=request.client.host)

        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info("Request completed",
                   status_code=response.status_code,
                   duration_ms=int(duration * 1000))

        return response
```

### **5. Dependency Injection**

#### **Use Case Dependencies**
```python
# Dependency providers
async def get_bot_repository() -> IBotRepository:
    return SqlAlchemyBotRepository()

async def get_ai_service() -> IAIService:
    return OpenAIService(api_key=os.getenv("OPENAI_API_KEY"))

async def get_bot_use_cases(
    bot_repository: IBotRepository = Depends(get_bot_repository)
) -> BotUseCases:
    return BotUseCases(bot_repository)

# Usage in routes
@router.post("/bots")
async def create_bot(
    request: CreateBotRequest,
    bot_use_cases: BotUseCases = Depends(get_bot_use_cases)
):
    # Route implementation
```

## 🚀 **Key Features**

### **1. Automatic API Documentation**
- **OpenAPI/Swagger** generation
- **Interactive docs** at `/docs`
- **ReDoc documentation** at `/redoc`
- **Schema validation** with Pydantic

### **2. Request Validation**
```python
class CreateBotRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    bot_type: str = Field(..., regex="^(customer_service|sales|support|general)$")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
```

### **3. Response Serialization**
```python
class BotResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
```

### **4. CORS & Security**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📊 **API Specification**

### **OpenAPI Schema**
```yaml
openapi: 3.0.0
info:
  title: Chat Orchestrator API
  version: 1.0.0
  description: Chat Orchestrator Core Backend API

paths:
  /api/v1/bots:
    post:
      summary: Create new bot
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateBotRequest'
      responses:
        201:
          description: Bot created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BotResponse'
```

### **Response Status Codes**
```
200 OK          - Successful operation
201 Created     - Resource created
204 No Content  - Successful deletion
400 Bad Request - Invalid input
404 Not Found   - Resource not found
422 Unprocessable Entity - Validation error
500 Internal Server Error - Server error
```

## 🧪 **Testing Strategy**

### **1. API Testing**
```python
@pytest.mark.asyncio
async def test_create_bot():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bots",
            json={
                "name": "Test Bot",
                "bot_type": "customer_service",
                "core_ai_id": str(uuid4()),
                "platform_id": str(uuid4()),
                "config": {
                    "ai_provider": "openai",
                    "ai_model": "gpt-3.5-turbo"
                }
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Bot"
```

### **2. Validation Testing**
```python
async def test_create_bot_validation_error():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bots",
            json={"name": ""}  # Invalid empty name
        )

        assert response.status_code == 422
        error = response.json()
        assert "name" in error["detail"][0]["loc"]
```

## 📈 **Performance Optimizations**

### **1. Async Operations**
```python
# All endpoints are async
@router.get("/bots")
async def list_bots():
    # Non-blocking operations
    bots = await bot_use_cases.search_bots(search_dto)
    return BotListResponse.from_dto(bots)
```

### **2. Response Compression**
```python
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### **3. Caching Headers**
```python
@router.get("/bots/{bot_id}")
async def get_bot(bot_id: UUID, response: Response):
    bot = await bot_use_cases.get_bot_by_id(bot_id)

    # Add caching headers
    response.headers["Cache-Control"] = "max-age=300"

    return BotResponse.from_dto(bot)
```

## 🔒 **Security Considerations**

### **1. Input Validation**
- **Pydantic models** for request validation
- **Field constraints** (min/max length, regex)
- **Type checking** and conversion
- **XSS prevention** through escaping

### **2. Rate Limiting**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/bots")
@limiter.limit("10/minute")
async def create_bot(request: Request):
    # Rate limited endpoint
```

### **3. Authentication (Future)**
```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@router.get("/bots")
async def list_bots(token: str = Depends(security)):
    # Authenticated endpoint
```

## 📊 **Monitoring & Observability**

### **1. Request Metrics**
```python
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

@router.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)

    request_count.inc()
    request_duration.observe(time.time() - start_time)

    return response
```

### **2. Health Endpoints**
```python
@router.get("/health")
async def health_check():
    checks = {
        'database': await check_database_health(),
        'ai_service': await ai_service.health_check()
    }

    status = "healthy" if all(checks.values()) else "unhealthy"

    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.utcnow()
    }
```

## 🚀 **Deployment**

### **1. Docker Configuration**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.presentation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **2. Production Settings**
```python
# Production configuration
app = create_app(
    debug=False,
    title="Chat Orchestrator API",
    version="1.0.0"
)

# Security headers
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.chatorch.com"]
)
```

---

**Presentation Layer provides a modern, scalable REST API for the Chat Orchestrator system! 🚀**