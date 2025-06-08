"""
Environment Template Generator
Generates environment configuration templates for different environments
"""
from typing import Dict, Any
from .settings import Environment


class EnvironmentTemplate:
    """Generate environment configuration templates"""

    @staticmethod
    def generate_template(environment: Environment = Environment.DEVELOPMENT) -> str:
        """Generate environment file template"""

        base_template = """# ==========================================
# 🚀 CHAT ORCHESTRATOR CONFIGURATION
# ==========================================

# ==========================================
# 🖥️ APPLICATION SETTINGS
# ==========================================
APP_NAME=Chat Orchestrator
APP_VERSION=1.0.0
APP_DESCRIPTION=Chat Orchestrator Core Backend

# Environment: development, testing, staging, production
ENVIRONMENT={environment}
DEBUG={debug}

# Server settings
HOST=0.0.0.0
PORT=8000
WORKERS=1

# Documentation
ENABLE_DOCS={enable_docs}
DOCS_URL=/docs
REDOC_URL=/redoc

# ==========================================
# 🗄️ DATABASE CONFIGURATION
# ==========================================
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
DB_ECHO={db_echo}

# Health check
DB_HEALTH_CHECK_TIMEOUT=5

# ==========================================
# 🤖 AI SERVICE CONFIGURATION
# ==========================================
# OpenAI Configuration
AI_OPENAI_API_KEY=your-openai-api-key
AI_OPENAI_ORGANIZATION=your-org-id-here
AI_OPENAI_BASE_URL=https://api.openai.com/v1

# Default model settings
AI_DEFAULT_MODEL=gpt-3.5-turbo
AI_DEFAULT_TEMPERATURE=0.7
AI_DEFAULT_MAX_TOKENS=1000

# Timeout and retry settings
AI_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=3
AI_RETRY_DELAY=1.0

# Rate limiting
AI_RATE_LIMIT_REQUESTS_PER_MINUTE=60
AI_RATE_LIMIT_TOKENS_PER_MINUTE=40000

# Content safety
AI_ENABLE_CONTENT_FILTERING=true
AI_CONTENT_FILTER_THRESHOLD=0.8

# Feature flags
AI_ENABLE_STREAMING=false
AI_ENABLE_FUNCTION_CALLING=true

# ==========================================
# 🌐 PLATFORM SERVICE CONFIGURATION
# ==========================================
# Telegram Bot Configuration
PLATFORM_TELEGRAM_BOT_TOKEN=your-telegram-bot-token
PLATFORM_TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
PLATFORM_TELEGRAM_WEBHOOK_SECRET=your-webhook-secret

# Facebook Messenger Configuration
PLATFORM_FACEBOOK_APP_ID=your-facebook-app-id
PLATFORM_FACEBOOK_APP_SECRET=your-facebook-app-secret
PLATFORM_FACEBOOK_ACCESS_TOKEN=your-facebook-access-token
PLATFORM_FACEBOOK_VERIFY_TOKEN=your-facebook-verify-token

# Discord Configuration
PLATFORM_DISCORD_BOT_TOKEN=your-discord-bot-token
PLATFORM_DISCORD_APPLICATION_ID=your-discord-app-id

# WhatsApp Configuration
PLATFORM_WHATSAPP_ACCESS_TOKEN=your-whatsapp-token
PLATFORM_WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
PLATFORM_WHATSAPP_WEBHOOK_VERIFY_TOKEN=your-whatsapp-verify-token

# Common platform settings
PLATFORM_TIMEOUT_SECONDS=30
PLATFORM_MAX_RETRIES=3
PLATFORM_RATE_LIMIT_REQUESTS_PER_MINUTE=30

# ==========================================
# 📧 NOTIFICATION SERVICE CONFIGURATION
# ==========================================
# SMTP Email Configuration
NOTIFICATION_SMTP_HOST=smtp.gmail.com
NOTIFICATION_SMTP_PORT=587
NOTIFICATION_SMTP_USERNAME=your-email@gmail.com
NOTIFICATION_SMTP_PASSWORD=your-app-password
NOTIFICATION_SMTP_USE_TLS=true

# Email defaults
NOTIFICATION_DEFAULT_FROM_EMAIL=noreply@chatorch.com
NOTIFICATION_DEFAULT_FROM_NAME=Chat Orchestrator

# Templates
NOTIFICATION_EMAIL_TEMPLATE_DIR=templates/email

# Push notifications
NOTIFICATION_FCM_SERVER_KEY=your-fcm-server-key
NOTIFICATION_APNS_KEY_ID=your-apns-key-id
NOTIFICATION_APNS_TEAM_ID=your-apns-team-id
NOTIFICATION_APNS_BUNDLE_ID=your-apns-bundle-id

# Timeout and retry
NOTIFICATION_TIMEOUT_SECONDS=30
NOTIFICATION_MAX_RETRIES=3

# ==========================================
# 🔴 CACHE CONFIGURATION (Redis)
# ==========================================
CACHE_REDIS_HOST=localhost
CACHE_REDIS_PORT=6379
CACHE_REDIS_DB=0
CACHE_REDIS_PASSWORD=
CACHE_REDIS_USERNAME=

# Connection settings
CACHE_REDIS_MAX_CONNECTIONS=10
CACHE_REDIS_SOCKET_TIMEOUT=30
CACHE_REDIS_CONNECTION_TIMEOUT=10

# Cache settings
CACHE_DEFAULT_TTL=3600
CACHE_CONVERSATION_TTL=86400
CACHE_SESSION_TTL=1800

# Feature flags
CACHE_ENABLE_CACHE=true
CACHE_ENABLE_CACHE_COMPRESSION=true

# ==========================================
# 📊 LOGGING CONFIGURATION
# ==========================================
LOG_LEVEL={log_level}
LOG_ROOT_LEVEL=WARNING

# Log format
LOG_FORMAT_JSON=true
LOG_INCLUDE_TIMESTAMP=true
LOG_INCLUDE_TRACE_ID=true

# Log destinations
LOG_ENABLE_CONSOLE=true
LOG_ENABLE_FILE=false
LOG_FILE_PATH=/var/log/chat-orchestrator/app.log
LOG_FILE_MAX_SIZE=10485760
LOG_FILE_BACKUP_COUNT=5

# External logging
LOG_SENTRY_DSN=your-sentry-dsn
LOG_ENABLE_SENTRY={enable_sentry}

# ==========================================
# 🔐 SECURITY CONFIGURATION
# ==========================================
# Secret keys (CHANGE IN PRODUCTION!)
SECURITY_SECRET_KEY={secret_key}
SECURITY_JWT_SECRET_KEY={jwt_secret_key}

# JWT settings
SECURITY_JWT_ALGORITHM=HS256
SECURITY_JWT_EXPIRATION_HOURS=24

# API keys
SECURITY_ADMIN_API_KEYS={admin_api_keys}
SECURITY_PLATFORM_ACCESS_TOKEN={platform_access_token}

# CORS settings
SECURITY_CORS_ORIGINS={cors_origins}
SECURITY_CORS_ALLOW_CREDENTIALS=true
SECURITY_CORS_ALLOW_METHODS=*
SECURITY_CORS_ALLOW_HEADERS=*

# Rate limiting
SECURITY_ENABLE_RATE_LIMITING={enable_rate_limiting}
SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE={rate_limit_rpm}
SECURITY_RATE_LIMIT_BURST=200

# Trusted hosts
SECURITY_TRUSTED_HOSTS={trusted_hosts}

# ==========================================
# 🏥 HEALTH CHECK
# ==========================================
HEALTH_CHECK_PATH=/health

# ==========================================
# 📝 NOTES
# ==========================================
# 1. Replace all 'your-*-here' values with actual credentials
# 2. Generate strong secret keys for production
# 3. Configure proper CORS origins for production
# 4. Set up proper database credentials
# 5. Configure email SMTP settings
# 6. Set environment-specific logging levels
# 7. Enable Sentry for production error tracking
"""

        # Environment-specific values
        template_values = {
            Environment.DEVELOPMENT: {
                'environment': 'development',
                'debug': 'true',
                'enable_docs': 'true',
                'db_echo': 'true',
                'log_level': 'DEBUG',
                'enable_sentry': 'false',
                'secret_key': 'dev-secret-key-change-in-production',
                'jwt_secret_key': 'dev-jwt-secret-key-change-in-production',
                'admin_api_keys': 'dev-admin-key,dev-admin-key-2',
                'platform_access_token': 'dev-platform-token',
                'cors_origins': '*',
                'enable_rate_limiting': 'false',
                'rate_limit_rpm': '1000',
                'trusted_hosts': '*'
            },
            Environment.TESTING: {
                'environment': 'testing',
                'debug': 'true',
                'enable_docs': 'false',
                'db_echo': 'false',
                'log_level': 'DEBUG',
                'enable_sentry': 'false',
                'secret_key': 'test-secret-key',
                'jwt_secret_key': 'test-jwt-secret-key',
                'admin_api_keys': 'test-admin-key',
                'platform_access_token': 'test-platform-token',
                'cors_origins': 'http://localhost:3000',
                'enable_rate_limiting': 'false',
                'rate_limit_rpm': '1000',
                'trusted_hosts': 'localhost,127.0.0.1'
            },
            Environment.STAGING: {
                'environment': 'staging',
                'debug': 'false',
                'enable_docs': 'true',
                'db_echo': 'false',
                'log_level': 'INFO',
                'enable_sentry': 'true',
                'secret_key': 'CHANGE-THIS-STAGING-SECRET-KEY',
                'jwt_secret_key': 'CHANGE-THIS-STAGING-JWT-SECRET',
                'admin_api_keys': 'staging-admin-key-1,staging-admin-key-2',
                'platform_access_token': 'staging-platform-token',
                'cors_origins': 'https://staging.chatorch.com',
                'enable_rate_limiting': 'true',
                'rate_limit_rpm': '200',
                'trusted_hosts': 'staging.chatorch.com,api-staging.chatorch.com'
            },
            Environment.PRODUCTION: {
                'environment': 'production',
                'debug': 'false',
                'enable_docs': 'false',
                'db_echo': 'false',
                'log_level': 'INFO',
                'enable_sentry': 'true',
                'secret_key': 'CHANGE-THIS-PRODUCTION-SECRET-KEY',
                'jwt_secret_key': 'CHANGE-THIS-PRODUCTION-JWT-SECRET',
                'admin_api_keys': 'prod-admin-key-1,prod-admin-key-2',
                'platform_access_token': 'production-platform-token',
                'cors_origins': 'https://chatorch.com,https://app.chatorch.com',
                'enable_rate_limiting': 'true',
                'rate_limit_rpm': '100',
                'trusted_hosts': 'chatorch.com,api.chatorch.com'
            }
        }

        values = template_values.get(environment, template_values[Environment.DEVELOPMENT])
        return base_template.format(**values)

    @staticmethod
    def generate_docker_env() -> str:
        """Generate Docker environment template"""
        return """# ==========================================
# 🐳 DOCKER ENVIRONMENT CONFIGURATION
# ==========================================

# Database (PostgreSQL container)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=chat_orchestrator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Redis (Redis container)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Application
ENVIRONMENT=development
DEBUG=true

# External services (add your API keys)
AI_OPENAI_API_KEY=your-openai-api-key
PLATFORM_TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# Security (change these!)
SECURITY_SECRET_KEY=docker-dev-secret-key
SECURITY_JWT_SECRET_KEY=docker-dev-jwt-secret-key
"""

    @staticmethod
    def generate_kubernetes_configmap() -> str:
        """Generate Kubernetes ConfigMap template"""
        return """apiVersion: v1
kind: ConfigMap
metadata:
  name: chat-orchestrator-config
  namespace: default
data:
  ENVIRONMENT: "production"
  DEBUG: "false"

  # Database
  DB_HOST: "postgres-service"
  DB_PORT: "5432"
  DB_NAME: "chat_orchestrator"
  DB_USER: "postgres"

  # Redis
  CACHE_REDIS_HOST: "redis-service"
  CACHE_REDIS_PORT: "6379"
  CACHE_REDIS_DB: "0"

  # Application
  HOST: "0.0.0.0"
  PORT: "8000"
  ENABLE_DOCS: "false"

  # Logging
  LOG_LEVEL: "INFO"
  LOG_FORMAT_JSON: "true"

  # Security
  SECURITY_CORS_ORIGINS: "https://chatorch.com"
  SECURITY_ENABLE_RATE_LIMITING: "true"

---
apiVersion: v1
kind: Secret
metadata:
  name: chat-orchestrator-secrets
  namespace: default
type: Opaque
stringData:
  DB_PASSWORD: "your-db-password"
  AI_OPENAI_API_KEY: "your-openai-api-key"
  PLATFORM_TELEGRAM_BOT_TOKEN: "your-telegram-token"
  SECURITY_SECRET_KEY: "your-production-secret-key"
  SECURITY_JWT_SECRET_KEY: "your-production-jwt-secret"
  LOG_SENTRY_DSN: "your-sentry-dsn"
"""

    @staticmethod
    def save_template(environment: Environment, filename: str = None) -> str:
        """Save environment template to file"""
        if filename is None:
            filename = f".env.{environment.value}"

        template = EnvironmentTemplate.generate_template(environment)

        with open(filename, 'w') as f:
            f.write(template)

        return filename


def generate_all_templates():
    """Generate all environment templates"""
    templates = {
        'development': EnvironmentTemplate.generate_template(Environment.DEVELOPMENT),
        'testing': EnvironmentTemplate.generate_template(Environment.TESTING),
        'staging': EnvironmentTemplate.generate_template(Environment.STAGING),
        'production': EnvironmentTemplate.generate_template(Environment.PRODUCTION),
        'docker': EnvironmentTemplate.generate_docker_env(),
        'kubernetes': EnvironmentTemplate.generate_kubernetes_configmap()
    }

    return templates