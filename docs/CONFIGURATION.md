# Configuration Management - Chat Orchestrator

## 🎯 **Overview**

The Chat Orchestrator uses a **centralized configuration management system** built with Pydantic Settings for type safety, validation, and environment-based configuration.

## 🏗️ **Architecture**

```
📁 app/infrastructure/config/
├── __init__.py           # Export configuration classes
├── settings.py           # Main configuration classes
├── factory.py            # Configuration factory and service creation
├── env_template.py       # Environment template generation
└── cli.py               # CLI tools for configuration management
```

## 📝 **Configuration Structure**

### **Main Settings Class**
```python
from app.infrastructure.config import get_settings

settings = get_settings()
```

### **Configuration Subsections**

1. **Database Configuration** (`settings.database`)
2. **AI Service Configuration** (`settings.ai_service`)
3. **Platform Service Configuration** (`settings.platform_service`)
4. **Notification Service Configuration** (`settings.notification_service`)
5. **Cache Configuration** (`settings.cache`)
6. **Logging Configuration** (`settings.logging`)
7. **Security Configuration** (`settings.security`)

## 🚀 **Quick Start**

### **1. Generate Environment File**
```bash
# Generate development environment template
python -m app.infrastructure.config.cli generate development --output .env

# Generate production environment template
python -m app.infrastructure.config.cli generate production --output .env.prod

# Generate all environment templates
python -m app.infrastructure.config.cli generate-all
```

### **2. Basic Configuration**
```bash
# Minimal .env file
ENVIRONMENT=development
DEBUG=true

# Database
DB_HOST=localhost
DB_PASSWORD=your-password

# AI Service
AI_OPENAI_API_KEY=your-openai-api-key

# Security
SECURITY_SECRET_KEY=your-secret-key
```

### **3. Validate Configuration**
```bash
# Validate current configuration
python -m app.infrastructure.config.cli validate

# Show current configuration
python -m app.infrastructure.config.cli show

# Test service connections
python -m app.infrastructure.config.cli test-services
```

## 🔧 **Configuration Sections**

### **1. Application Settings**
```bash
# Application
APP_NAME=Chat Orchestrator
APP_VERSION=1.0.0
APP_DESCRIPTION=Chat Orchestrator Core Backend

# Environment
ENVIRONMENT=development  # development, testing, staging, production
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=1

# Documentation
ENABLE_DOCS=true
DOCS_URL=/docs
REDOC_URL=/redoc
```

### **2. Database Configuration**
```bash
# Connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chat_orchestrator
DB_USER=postgres
DB_PASSWORD=postgres
DB_DRIVER=postgresql+asyncpg

# Pool settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Query settings
DB_ECHO=false
DB_HEALTH_CHECK_TIMEOUT=5
```

### **3. AI Service Configuration**
```bash
# OpenAI
AI_OPENAI_API_KEY=your-api-key
AI_OPENAI_ORGANIZATION=your-org-id
AI_OPENAI_BASE_URL=https://api.openai.com/v1

# Default model settings
AI_DEFAULT_MODEL=gpt-3.5-turbo
AI_DEFAULT_TEMPERATURE=0.7
AI_DEFAULT_MAX_TOKENS=1000

# Timeout and retry
AI_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=3
AI_RETRY_DELAY=1.0

# Rate limiting
AI_RATE_LIMIT_REQUESTS_PER_MINUTE=60
AI_RATE_LIMIT_TOKENS_PER_MINUTE=40000

# Content safety
AI_ENABLE_CONTENT_FILTERING=true
AI_CONTENT_FILTER_THRESHOLD=0.8

# Features
AI_ENABLE_STREAMING=false
AI_ENABLE_FUNCTION_CALLING=true
```

### **4. Platform Services**
```bash
# Telegram
PLATFORM_TELEGRAM_BOT_TOKEN=your-bot-token
PLATFORM_TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
PLATFORM_TELEGRAM_WEBHOOK_SECRET=your-webhook-secret

# Facebook
PLATFORM_FACEBOOK_APP_ID=your-app-id
PLATFORM_FACEBOOK_APP_SECRET=your-app-secret
PLATFORM_FACEBOOK_ACCESS_TOKEN=your-access-token
PLATFORM_FACEBOOK_VERIFY_TOKEN=your-verify-token

# Discord
PLATFORM_DISCORD_BOT_TOKEN=your-discord-token
PLATFORM_DISCORD_APPLICATION_ID=your-discord-app-id

# WhatsApp
PLATFORM_WHATSAPP_ACCESS_TOKEN=your-whatsapp-token
PLATFORM_WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
PLATFORM_WHATSAPP_WEBHOOK_VERIFY_TOKEN=your-verify-token

# Common settings
PLATFORM_TIMEOUT_SECONDS=30
PLATFORM_MAX_RETRIES=3
PLATFORM_RATE_LIMIT_REQUESTS_PER_MINUTE=30
```

### **5. Cache Configuration (Redis)**
```bash
# Redis connection
CACHE_REDIS_HOST=localhost
CACHE_REDIS_PORT=6379
CACHE_REDIS_DB=0
CACHE_REDIS_PASSWORD=your-redis-password
CACHE_REDIS_USERNAME=your-redis-username

# Connection settings
CACHE_REDIS_MAX_CONNECTIONS=10
CACHE_REDIS_SOCKET_TIMEOUT=30
CACHE_REDIS_CONNECTION_TIMEOUT=10

# Cache settings
CACHE_DEFAULT_TTL=3600
CACHE_CONVERSATION_TTL=86400
CACHE_SESSION_TTL=1800

# Features
CACHE_ENABLE_CACHE=true
CACHE_ENABLE_CACHE_COMPRESSION=true
```

### **6. Security Configuration**
```bash
# Secret keys
SECURITY_SECRET_KEY=your-secret-key
SECURITY_JWT_SECRET_KEY=your-jwt-secret

# JWT settings
SECURITY_JWT_ALGORITHM=HS256
SECURITY_JWT_EXPIRATION_HOURS=24

# API keys
SECURITY_ADMIN_API_KEYS=admin-key-1,admin-key-2
SECURITY_PLATFORM_ACCESS_TOKEN=platform-token

# CORS
SECURITY_CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
SECURITY_CORS_ALLOW_CREDENTIALS=true
SECURITY_CORS_ALLOW_METHODS=*
SECURITY_CORS_ALLOW_HEADERS=*

# Rate limiting
SECURITY_ENABLE_RATE_LIMITING=true
SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE=100
SECURITY_RATE_LIMIT_BURST=200

# Trusted hosts
SECURITY_TRUSTED_HOSTS=your-domain.com,api.your-domain.com
```

### **7. Logging Configuration**
```bash
# Log levels
LOG_LEVEL=INFO
LOG_ROOT_LEVEL=WARNING

# Format
LOG_FORMAT_JSON=true
LOG_INCLUDE_TIMESTAMP=true
LOG_INCLUDE_TRACE_ID=true

# Destinations
LOG_ENABLE_CONSOLE=true
LOG_ENABLE_FILE=false
LOG_FILE_PATH=/var/log/chat-orchestrator/app.log
LOG_FILE_MAX_SIZE=10485760
LOG_FILE_BACKUP_COUNT=5

# External logging
LOG_SENTRY_DSN=your-sentry-dsn
LOG_ENABLE_SENTRY=false
```

## 🔧 **Using Configuration in Code**

### **1. Basic Usage**
```python
from app.infrastructure.config import get_settings

# Get settings instance
settings = get_settings()

# Access database configuration
db_url = settings.database.url
pool_size = settings.database.pool_size

# Access AI service configuration
api_key = settings.ai_service.openai_api_key
model = settings.ai_service.default_model
```

### **2. Configuration Factory**
```python
from app.infrastructure.config import get_configuration_factory

# Get factory instance
factory = get_configuration_factory()

# Initialize all infrastructure
services = await factory.initialize_infrastructure()

# Create individual services
ai_service = factory.create_ai_service()
platform_service = factory.create_platform_service()
```

### **3. Environment-Specific Settings**
```python
from app.infrastructure.config import get_settings

settings = get_settings()

# Check environment
if settings.is_production():
    # Production-specific logic
    pass
elif settings.is_development():
    # Development-specific logic
    pass
```

## 🌍 **Environment-Specific Configuration**

### **Development Environment**
```bash
ENVIRONMENT=development
DEBUG=true
ENABLE_DOCS=true
DB_ECHO=true
LOG_LEVEL=DEBUG
SECURITY_CORS_ORIGINS=*
SECURITY_ENABLE_RATE_LIMITING=false
```

### **Testing Environment**
```bash
ENVIRONMENT=testing
DEBUG=true
ENABLE_DOCS=false
DB_ECHO=false
LOG_LEVEL=DEBUG
SECURITY_CORS_ORIGINS=http://localhost:3000
SECURITY_ENABLE_RATE_LIMITING=false
```

### **Production Environment**
```bash
ENVIRONMENT=production
DEBUG=false
ENABLE_DOCS=false
DB_ECHO=false
LOG_LEVEL=INFO
LOG_ENABLE_SENTRY=true
SECURITY_CORS_ORIGINS=https://your-domain.com
SECURITY_ENABLE_RATE_LIMITING=true
```

## 🐳 **Docker Configuration**

### **Docker Compose Environment**
```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    environment:
      - ENVIRONMENT=development
      - DB_HOST=postgres
      - CACHE_REDIS_HOST=redis
      - AI_OPENAI_API_KEY=${OPENAI_API_KEY}

  postgres:
    environment:
      - POSTGRES_DB=chat_orchestrator
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres

  redis:
    image: redis:alpine
```

### **Kubernetes Configuration**
```yaml
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: chat-orchestrator-config
data:
  ENVIRONMENT: "production"
  DB_HOST: "postgres-service"
  CACHE_REDIS_HOST: "redis-service"

---
# Secret
apiVersion: v1
kind: Secret
metadata:
  name: chat-orchestrator-secrets
type: Opaque
stringData:
  DB_PASSWORD: "your-db-password"
  AI_OPENAI_API_KEY: "your-openai-key"
  SECURITY_SECRET_KEY: "your-secret-key"
```

## 🛠️ **CLI Tools**

### **Available Commands**
```bash
# Validate configuration
python -m app.infrastructure.config.cli validate

# Show current configuration
python -m app.infrastructure.config.cli show

# Generate environment templates
python -m app.infrastructure.config.cli generate development
python -m app.infrastructure.config.cli generate production --output .env.prod

# Test service connections
python -m app.infrastructure.config.cli test-services

# Generate all templates
python -m app.infrastructure.config.cli generate-all
```

### **Configuration Validation Output**
```
🔍 Configuration Validation Results:
==================================================
DATABASE            ✅ VALID
AI_SERVICE           ✅ VALID
SECURITY             ✅ VALID

🎉 All configuration components are valid!
```

### **Configuration Display Output**
```
📋 Current Configuration:
==================================================

🖥️  Application:
  Name: Chat Orchestrator
  Version: 1.0.0
  Environment: development
  Debug: True
  Host: 0.0.0.0:8000

🗄️  Database:
  Host: localhost:5432
  Database: chat_orchestrator
  User: postgres
  Pool Size: 10
  Echo: True

🤖 AI Service:
  Base URL: https://api.openai.com/v1
  API Key: ***key4
  Default Model: gpt-3.5-turbo
  Timeout: 30s
  Content Filtering: True
```

## 🔒 **Security Best Practices**

### **1. Environment Variables**
- Never commit `.env` files to version control
- Use different secret keys for each environment
- Rotate API keys regularly
- Use strong passwords for database connections

### **2. Production Configuration**
```bash
# Strong secret keys (generate with secrets.token_urlsafe(32))
SECURITY_SECRET_KEY=your-strong-32-byte-secret-key
SECURITY_JWT_SECRET_KEY=your-strong-jwt-secret-key

# Restricted CORS origins
SECURITY_CORS_ORIGINS=https://yourdomain.com

# Enable rate limiting
SECURITY_ENABLE_RATE_LIMITING=true

# Trusted hosts only
SECURITY_TRUSTED_HOSTS=yourdomain.com,api.yourdomain.com
```

### **3. API Key Management**
```bash
# Use separate API keys for different environments
# Development
AI_OPENAI_API_KEY=sk-dev-...

# Production
AI_OPENAI_API_KEY=sk-prod-...

# Admin API keys (comma-separated for multiple keys)
SECURITY_ADMIN_API_KEYS=admin-key-1,admin-key-2,admin-key-3
```

## 🚀 **Deployment Examples**

### **Local Development**
```bash
# 1. Generate development environment
python -m app.infrastructure.config.cli generate development --output .env

# 2. Edit .env with your credentials
nano .env

# 3. Validate configuration
python -m app.infrastructure.config.cli validate

# 4. Start application
uvicorn app.presentation.api.main:app --reload
```

### **Production Deployment**
```bash
# 1. Generate production environment template
python -m app.infrastructure.config.cli generate production --output .env.prod

# 2. Configure production values
nano .env.prod

# 3. Set environment file
export ENV_FILE=.env.prod

# 4. Validate production configuration
python -m app.infrastructure.config.cli validate

# 5. Deploy application
uvicorn app.presentation.api.main:app --host 0.0.0.0 --port 8000
```

---

**The configuration system provides a solid foundation for managing Chat Orchestrator across all environments! 🔧**