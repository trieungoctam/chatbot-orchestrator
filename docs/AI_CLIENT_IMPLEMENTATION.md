# AI Client Implementation Guide

## Overview

The AI Client Implementation provides a robust, database-driven system for calling AI APIs using bot configuration data. The system supports both development (mock) and production (real API) environments with automatic fallback mechanisms and comprehensive error handling. **The system now uses standard array format for role and content**, making it compatible with modern AI APIs like OpenAI's ChatGPT format.

## 🏗️ Architecture

### Core Components

#### 1. **DatabaseAIService**
- **Purpose**: Production AI service that uses CoreAI configuration from database
- **Features**:
  - Configuration caching (5-minute TTL)
  - Database-driven AI endpoint management
  - Authentication token handling
  - Timeout and retry configuration
  - Health monitoring
  - **Array format message processing**

#### 2. **MockAIService**
- **Purpose**: Development and testing AI service with simulated responses
- **Features**:
  - Intelligent response generation based on message content
  - Configurable processing delays
  - Healthcare-focused mock responses
  - **Conversation context awareness with array format**
  - Enhanced symptom recognition

#### 3. **Service Selection**
```python
def get_ai_service() -> Union[DatabaseAIService, MockAIService]:
    """Get AI service instance based on environment."""
    if settings.ENVIRONMENT == "development":
        return mock_ai_service
    else:
        return database_ai_service
```

## 🎯 Key Features

### Array Format for Messages
The system now uses the **standard array format** for role and content, compatible with modern AI APIs:

```python
# New Array Format (OpenAI compatible)
messages = [
    {"role": "user", "content": "Hello doctor"},
    {"role": "assistant", "content": "Hello! How can I help you today?"},
    {"role": "user", "content": "I have a headache and fever"}
]

# Old Format (deprecated)
message = "<USER>Hello doctor</USER>\n<ASSISTANT>Hello! How can I help?</ASSISTANT>\n<USER>I have a headache</USER>"
```

### Enhanced Mock AI Responses
The MockAI now provides more intelligent healthcare-focused responses:

| Input Pattern | Response Type | Example Response | Actions |
|---------------|---------------|------------------|---------|
| "headache", "pain" | Symptom Inquiry | "I understand you're experiencing discomfort..." | symptom_assessment |
| "fever", "temperature" | Fever Assessment | "Fever can be concerning..." | temperature_check |
| "appointment", "book" | Appointment | "I can help you book an appointment..." | show_calendar |
| "doctor" | Doctor Lookup | "Here are our available doctors..." | list_doctors |
| "hello", "hi" | Greeting | "Hello! How can I help you today?" | None |

### Database-Driven Configuration
- **CoreAI Management**: AI configurations stored in database
- **Bot Integration**: Each bot links to specific AI configuration
- **Dynamic Updates**: Configuration changes without code deployment
- **Multi-Provider Support**: Support for multiple AI providers

### Smart Caching
- **5-Minute Cache**: Active configurations cached for performance
- **Automatic Refresh**: Cache invalidation on updates
- **Memory Efficient**: Only active configurations cached

### Authentication Support
- **Bearer Token**: Standard JWT/API key authentication
- **Configurable**: Per-AI-provider authentication settings
- **Secure**: Token management with database encryption support

### Error Handling & Resilience
- **Timeout Management**: Configurable per-provider timeouts
- **Connection Retries**: Automatic retry on network failures
- **Graceful Degradation**: Fallback to defaults on configuration errors
- **Comprehensive Logging**: Detailed error tracking and debugging

## 📋 Implementation Details

### AI Configuration Structure
```python
{
    "id": "uuid-string",
    "name": "GPT-4 Healthcare",
    "api_endpoint": "https://api.openai.com/v1/chat/completions",
    "timeout_seconds": 30,
    "auth_required": True,
    "auth_token": "bearer-token",
    "meta_data": {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000
    }
}
```

### Message Processing Flow (Array Format)
1. **Configuration Retrieval**: Get AI config from database/cache
2. **Message Array Preparation**: Build messages array with role/content
3. **Request Preparation**: Build API payload with messages array
4. **Authentication**: Add bearer tokens if required
5. **API Call**: HTTP POST to AI endpoint with timeout
6. **Response Processing**: Parse and validate AI response
7. **Result Formatting**: Standardize response format
8. **Performance Tracking**: Log processing times and metrics

### Job Processing Integration
```python
async def process_job(
    job_id: str,
    conversation_id: str,
    messages: List[Dict[str, Any]],  # Array format
    context: Optional[Dict[str, Any]] = None,
    core_ai_id: Optional[Union[str, uuid.UUID]] = None
) -> Dict[str, Any]:
    """Process a job through AI service with job tracking."""

    # Add job context
    job_context = context or {}
    job_context.update({
        "job_id": job_id,
        "processing_type": "background_job",
        "started_at": time.time(),
        "message_count": len(messages)
    })

    # Process with AI service using array format
    result = await self.process_message(
        conversation_id=conversation_id,
        messages=messages,  # Pass messages array directly
        context=job_context,
        core_ai_id=core_ai_id
    )

    return result
```

## 🔧 Integration with Message Handler

### Background Job Processing
The AI client is integrated with the message handler's background job system:

```python
# In MessageHandler._process_ai_job()
ai_service = get_ai_service()

ai_result = await ai_service.process_job(
    job_id=job_id,
    conversation_id=conversation_id,
    messages=messages,  # Array format from parsed history
    context={
        "bot_config": bot_config,
        "ai_config": ai_config,
        "resources": payload.get("resources", {})
    },
    core_ai_id=ai_config.get("core_ai_id")
)
```

### Enhanced Job Status Tracking
- **Success Tracking**: Monitor successful AI processing
- **Error Handling**: Capture and log AI processing failures
- **Performance Metrics**: Track processing times and response quality
- **Provider Analytics**: Monitor usage by AI provider
- **Conversation Turns**: Track conversation length and context

## 🧪 Testing & Validation

### Array Format Testing
```python
# Test array format messages
messages = [
    {"role": "user", "content": "Hello doctor"},
    {"role": "assistant", "content": "Hello! How can I help you today?"},
    {"role": "user", "content": "I have a severe headache and fever"}
]

result = await ai_service.process_message(
    conversation_id='test-array-format',
    messages=messages,
    context={'format_test': True}
)

print(f"Conversation Turns: {result['conversation_turns']}")  # Output: 3
print(f"Intent: {result['intent']}")  # Output: symptom_inquiry
```

### Enhanced Mock AI Responses
The MockAIService now provides context-aware responses:

```python
# Input: Multi-turn conversation with symptoms
messages = [
    {"role": "user", "content": "Hello doctor"},
    {"role": "assistant", "content": "Hello! How can I help you?"},
    {"role": "user", "content": "I have a headache and fever"}
]

# Output: Intelligent healthcare response
{
    "response": "I understand you're experiencing discomfort. Can you describe your symptoms in more detail?",
    "intent": "symptom_inquiry",
    "confidence": 0.90,
    "actions": [
        {
            "type": "symptom_assessment",
            "data": {
                "symptoms": ["headache", "pain"],
                "follow_up_questions": ["duration", "severity", "location"]
            }
        }
    ],
    "conversation_turns": 3
}
```

### Test Coverage
```bash
# Run AI client tests
python -m pytest tests/test_ai_client.py -v

# Run integration tests with array format
python -m pytest tests/test_api_chat.py -v

# Test all components
python -m pytest tests/ -v

# Results: ✅ 22 tests passed
```

### Performance Testing
```python
# Example performance test with array format
result = await ai_service.process_message(
    conversation_id="perf-test",
    messages=[{"role": "user", "content": "Test message"}],
    context={"test": True}
)

print(f"Processing time: {result['processing_time_ms']}ms")
print(f"Conversation turns: {result['conversation_turns']}")
```

## 🚀 Production Deployment

### Environment Configuration
```bash
# Production environment
ENVIRONMENT=production
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Development environment
ENVIRONMENT=development
# Uses MockAIService automatically with enhanced responses
```

### AI Provider Setup
1. **Create CoreAI Configuration**:
   ```sql
   INSERT INTO core_ai (name, api_endpoint, auth_required, auth_token, timeout_seconds)
   VALUES ('GPT-4', 'https://api.openai.com/v1/chat/completions', true, 'sk-...', 30);
   ```

2. **Link Bot to AI**:
   ```sql
   UPDATE bots SET core_ai_id = '<core-ai-uuid>' WHERE name = 'Healthcare Bot';
   ```

3. **Test Array Format**:
   ```bash
   curl -X POST /api/v1/chat/message \
     -H "X-Access-Token: test-token" \
     -d '{
       "conversation_id": "test",
       "history": "<USER>Hello</USER><br><BOT>Hi there!</BOT><br><USER>I need help</USER><br>"
     }'
   ```

### Array Format API Payload
```json
{
    "conversation_id": "uuid",
    "messages": [
        {"role": "user", "content": "Hello doctor"},
        {"role": "assistant", "content": "Hello! How can I help?"},
        {"role": "user", "content": "I have symptoms"}
    ],
    "context": {
        "bot_config": {...},
        "ai_config": {...}
    }
}
```

### Monitoring & Metrics
- **AI Response Times**: Track processing latency per conversation turn
- **Success Rates**: Monitor AI processing success/failure rates
- **Intent Recognition**: Track intent classification accuracy
- **Conversation Quality**: Monitor conversation turn effectiveness
- **Symptom Detection**: Track healthcare-specific pattern recognition
- **Usage Analytics**: Track AI usage by bot and conversation
- **Cost Monitoring**: Monitor API costs by provider and conversation length

## 🔐 Security Considerations

### Authentication Token Management
- **Secure Storage**: Encrypt authentication tokens in database
- **Token Rotation**: Support for regular token updates
- **Access Control**: Limit token access to authorized services
- **Audit Logging**: Log all AI API access and usage

### Request Validation
- **Input Sanitization**: Clean and validate user inputs in message arrays
- **Rate Limiting**: Prevent abuse of AI services
- **Content Filtering**: Filter inappropriate content before AI processing
- **Response Validation**: Validate AI responses before returning
- **Message Array Validation**: Ensure proper role/content format

## 📈 Performance Optimization

### Caching Strategy
- **Configuration Cache**: 5-minute TTL for AI configurations
- **Response Cache**: Cache common AI responses (optional)
- **Connection Pooling**: Reuse HTTP connections to AI providers
- **Async Processing**: Non-blocking AI processing with background jobs
- **Message Parsing**: Efficient array parsing from history strings

### Scaling Considerations
- **Horizontal Scaling**: Multiple handler instances with shared cache
- **Load Balancing**: Distribute AI requests across multiple endpoints
- **Circuit Breaking**: Prevent cascade failures from AI providers
- **Timeout Management**: Prevent resource exhaustion from slow AI calls
- **Conversation Context**: Efficient handling of long conversation histories

## 🛠️ Troubleshooting

### Common Issues

#### 1. Array Format Errors
```
Error: Expected array format for messages
Solution: Ensure messages are in [{"role": "...", "content": "..."}] format
```

#### 2. Conversation Context Issues
```
Error: Missing conversation context
Solution: Check message parsing from history string format
```

#### 3. AI Configuration Not Found
```
Error: No active CoreAI configuration found
Solution: Check database for active CoreAI entries
```

#### 4. Authentication Failures
```
Error: AI service returned 401: Unauthorized
Solution: Verify auth_token in CoreAI configuration
```

### Debug Commands
```bash
# Test array format processing
python -c "
import asyncio
from app.clients.core_ai_client import get_ai_service

async def test():
    ai = get_ai_service()
    messages = [{'role': 'user', 'content': 'Hello'}]
    result = await ai.process_message('test', messages)
    print(f'Turns: {result.get(\"conversation_turns\")}')

asyncio.run(test())
"

# Clear AI cache
python -c "
from app.clients.core_ai_client import get_ai_service
ai = get_ai_service()
ai.clear_cache()
print('Cache cleared')
"
```

## 📚 Related Documentation

- [Message Handler Documentation](MESSAGE_HANDLER_DOCUMENTATION.md)
- [Job Cancellation Feature](JOB_CANCELLATION_FEATURE.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Database Schema](../alembic/versions/)
- [Core AI CRUD Operations](../app/crud/core_ai_crud.py)