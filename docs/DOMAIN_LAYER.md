# 🏛️ **DOMAIN LAYER DOCUMENTATION**

**Chat Orchestrator - Core Business Logic Documentation**

## 📖 **Overview**

Domain Layer là trung tâm của hệ thống Chat Orchestrator, chứa tất cả **Core Business Logic**, **Business Rules**, và **Domain Knowledge**. Layer này hoàn toàn độc lập với infrastructure và external concerns.

### **Key Principles**

- 🔒 **Encapsulation**: Business logic được đóng gói trong Domain Entities
- 🚫 **No Dependencies**: Không phụ thuộc vào external libraries hay frameworks
- 💡 **Rich Domain Model**: Entities chứa behavior thay vì chỉ data
- ⚖️ **Business Rules First**: Mọi operation đều validate business rules
- 🔄 **Immutability**: Value Objects và Entities state management an toàn

---

## 🏗️ **Architecture Overview**

```
📁 app/domain/
├── 📁 entities/           # Domain Entities (Aggregates)
│   ├── bot.py            # Bot Aggregate Root
│   ├── conversation.py   # Conversation Aggregate Root
│   └── message.py        # Message Entity
├── 📁 value_objects/     # Immutable Value Objects
│   ├── bot_config.py     # Bot Configuration
│   └── conversation_context.py  # Conversation Context
├── 📁 services/          # Domain Services
│   └── conversation_orchestrator.py  # Complex Business Logic
├── 📁 repositories/      # Repository Interfaces
│   ├── bot_repository.py
│   └── conversation_repository.py
└── exceptions.py         # Domain Exceptions
```

---

## 🎯 **DOMAIN ENTITIES**

### **1. Bot Entity** (`bot.py`)

**Aggregate Root** quản lý chatbot configurations và business logic.

#### **Business Rules:**
1. ✅ Bot name must be unique và không empty
2. ✅ Bot phải có CoreAI và Platform valid
3. ✅ Bot chỉ xử lý message khi status = ACTIVE
4. ✅ Bot có giới hạn conversation đồng thời
5. ✅ Bot có expiration date (optional)

#### **Key Methods:**
```python
# Lifecycle Management
bot.activate() -> Bot
bot.deactivate() -> Bot
bot.start_maintenance() -> Bot

# Business Logic
bot.can_handle_new_conversation() -> bool
bot.can_handle_language(language: str) -> bool
bot.start_conversation() -> Bot
bot.end_conversation() -> Bot

# Configuration
bot.update_config(new_config: BotConfig) -> Bot

# Queries
bot.is_operational() -> bool
bot.get_load_percentage() -> float
bot.is_overloaded(threshold: float) -> bool
```

#### **Usage Example:**
```python
from app.domain.entities.bot import Bot, BotStatus, BotType
from app.domain.value_objects.bot_config import BotConfig

# Create bot
bot = Bot(
    id=uuid4(),
    name="Customer Service Bot",
    bot_type=BotType.CUSTOMER_SERVICE,
    language="vi",
    core_ai_id=ai_id,
    platform_id=platform_id,
    config=bot_config,
    status=BotStatus.ACTIVE
)

# Business operations
if bot.can_handle_new_conversation():
    updated_bot = bot.start_conversation()
```

---

### **2. Conversation Entity** (`conversation.py`)

**Aggregate Root** quản lý chat session lifecycle và message coordination.

#### **Business Rules:**
1. ✅ Conversation có unique external ID
2. ✅ Chỉ accept message khi status = ACTIVE
3. ✅ Auto timeout sau idle time
4. ✅ Giới hạn message count
5. ✅ Track conversation context

#### **Key Methods:**
```python
# Message Management
conversation.add_message(content, role, metadata) -> Message
conversation.can_accept_messages() -> bool

# Lifecycle
conversation.pause(reason) -> None
conversation.resume() -> None
conversation.end(reason) -> None
conversation.handle_timeout() -> None

# Transfer & Escalation
conversation.transfer_to_human(agent_id, reason) -> None
conversation.escalate_priority(new_priority, reason) -> None

# Queries
conversation.is_active() -> bool
conversation.is_timed_out() -> bool
conversation.get_recent_messages(limit) -> List[Message]
conversation.needs_attention() -> bool
```

#### **Usage Example:**
```python
from app.domain.entities.conversation import Conversation, ConversationStatus

# Create conversation
conversation = Conversation(
    id=uuid4(),
    conversation_id="tg_123456_bot_20241201_143000",
    bot_id=bot_id,
    status=ConversationStatus.ACTIVE
)

# Add user message
message = conversation.add_message(
    content="Hello, I need help",
    role=MessageRole.USER,
    metadata={"platform": "telegram"}
)
```

---

### **3. Message Entity** (`message.py`)

Individual chat message với processing status và metadata.

#### **Business Rules:**
1. ✅ Message content cannot be empty
2. ✅ Content length limits based on type
3. ✅ Metadata validation for special types
4. ✅ Automatic language detection
5. ✅ Status lifecycle management

#### **Key Methods:**
```python
# Processing Lifecycle
message.mark_as_processing(ai_model) -> Message
message.mark_as_sent(processing_time_ms, confidence_score) -> Message
message.mark_as_failed(error_reason) -> Message
message.retry() -> Message

# Queries
message.is_user_message() -> bool
message.is_bot_message() -> bool
message.is_processing() -> bool
message.has_high_confidence(threshold) -> bool
```

---

## 💎 **VALUE OBJECTS**

### **1. BotConfig** (`bot_config.py`)

Immutable configuration cho Bot operations.

#### **Key Features:**
- ✅ AI Provider & Model validation
- ✅ Platform compatibility checks
- ✅ Resource limits enforcement
- ✅ Feature flags management
- ✅ Expiration handling

```python
from app.domain.value_objects.bot_config import BotConfig, AIProvider

config = BotConfig(
    ai_provider=AIProvider.OPENAI,
    ai_model="gpt-4",
    ai_temperature=0.7,
    platform_type=PlatformType.TELEGRAM,
    max_concurrent_users=100,
    enable_sentiment_analysis=True
)

# Immutable updates
new_config = config.update_ai_settings(temperature=0.8)
```

### **2. ConversationContext** (`conversation_context.py`)

Context state management cho conversations.

#### **Key Features:**
- 🔗 **External User Integration**: Làm việc với platform-specific user data
- 🧠 **Intent & Entity Tracking**: NLP results storage
- 😊 **Sentiment Analysis**: Conversation mood tracking
- 🏷️ **Context Flags**: Error và escalation indicators
- 📝 **System Notes**: Audit trail và debugging

```python
from app.domain.value_objects.conversation_context import ConversationContext

# Create context với external user data
context = ConversationContext.create_with_external_user(
    external_user_id="telegram_123456",
    platform="telegram",
    external_user_data={
        "first_name": "John",
        "language_code": "vi",
        "is_premium": True
    }
)

# Add business context
context = context.add_intent("ask_support", confidence=0.9)
context = context.add_entity("product", "iPhone 15", confidence=0.8)
context = context.update_sentiment("positive", 0.7)
```

---

## 🔧 **DOMAIN SERVICES**

### **ConversationOrchestrator** (`conversation_orchestrator.py`)

Orchestrates complex conversation business logic.

#### **Responsibilities:**
1. 🚀 **Conversation Lifecycle Management**
2. 📤 **Message Routing & Validation**
3. 🧠 **Context Management**
4. ⬆️ **Escalation Logic**
5. ⚖️ **Load Balancing**

#### **Key Methods:**

```python
# Start new conversation
conversation, message = orchestrator.start_conversation(
    bot=bot,
    initial_message="Hello",
    external_user_id="telegram_123456",
    platform="telegram",
    external_user_data=user_data
)

# Process user input
conversation, message = orchestrator.process_user_message(
    conversation=conversation,
    message_content="I need help",
    external_user_id="telegram_123456"
)

# Add bot response
conversation, response = orchestrator.add_bot_response(
    conversation=conversation,
    response_content="How can I help you?",
    confidence_score=0.95,
    ai_model="gpt-4"
)

# Handle escalation
conversation = orchestrator.escalate_conversation(
    conversation=conversation,
    reason="Low confidence responses",
    escalated_by="system"
)
```

---

## 🏛️ **REPOSITORY INTERFACES**

Domain định nghĩa contracts cho data access without implementation details.

### **IBotRepository**
```python
from app.domain.repositories.bot_repository import IBotRepository

# CRUD Operations
async def create(bot: Bot) -> Bot
async def get_by_id(bot_id: UUID) -> Optional[Bot]
async def update(bot: Bot) -> Bot

# Business Queries
async def list_active_bots() -> List[Bot]
async def get_overloaded_bots(threshold: float) -> List[Bot]
async def search_bots(query: str, filters: Dict) -> List[Bot]
```

### **IConversationRepository**
```python
# Conversation Management
async def create(conversation: Conversation) -> Conversation
async def get_by_external_id(external_id: str) -> Optional[Conversation]

# Business Queries
async def list_escalated_conversations() -> List[Conversation]
async def list_timed_out_conversations() -> List[Conversation]
async def get_bot_conversation_stats(bot_id, start_date, end_date) -> Dict
```

---

## ⚠️ **DOMAIN EXCEPTIONS**

Structured exception hierarchy cho business rule violations.

### **Exception Types:**

```python
from app.domain.exceptions import (
    DomainError,                    # Base domain exception
    BusinessRuleViolationError,     # Business rule violations
    EntityNotFoundError,            # Entity không tồn tại
    InvalidOperationError,          # Invalid state operations
    ConcurrencyError,              # Concurrent access conflicts
    ResourceLimitExceededError     # Resource limits exceeded
)

# Usage
try:
    bot = bot.activate()
except BusinessRuleViolationError as e:
    logger.error(f"Cannot activate bot: {e.message}")
    # Handle business rule violation
```

---

## 🔄 **BUSINESS WORKFLOWS**

### **1. Start New Conversation**

```python
def start_conversation_workflow(
    bot_id: UUID,
    external_user_id: str,
    platform: str,
    initial_message: str,
    external_user_data: Dict[str, Any]
):
    # 1. Get bot
    bot = await bot_repository.get_by_id(bot_id)

    # 2. Validate business rules
    orchestrator = ConversationOrchestrator()
    conversation, message = orchestrator.start_conversation(
        bot=bot,
        initial_message=initial_message,
        external_user_id=external_user_id,
        platform=platform,
        external_user_data=external_user_data
    )

    # 3. Persist conversation
    conversation = await conversation_repository.create(conversation)

    # 4. Update bot metrics
    updated_bot = bot.start_conversation()
    await bot_repository.update(updated_bot)

    return conversation
```

### **2. Process Message & Generate Response**

```python
def process_message_workflow(
    conversation_id: str,
    message_content: str,
    external_user_id: str
):
    # 1. Get conversation
    conversation = await conversation_repository.get_by_external_id(conversation_id)

    # 2. Process user message
    orchestrator = ConversationOrchestrator()
    conversation, user_message = orchestrator.process_user_message(
        conversation=conversation,
        message_content=message_content,
        external_user_id=external_user_id
    )

    # 3. Generate AI response
    ai_response = await ai_service.generate_response(
        message=message_content,
        context=conversation.context.get_context_summary()
    )

    # 4. Add bot response
    conversation, bot_message = orchestrator.add_bot_response(
        conversation=conversation,
        response_content=ai_response.content,
        confidence_score=ai_response.confidence,
        ai_model=ai_response.model
    )

    # 5. Check auto-escalation
    health_score = orchestrator.get_conversation_health_score(conversation)
    if health_score < 0.3:
        conversation = orchestrator.escalate_conversation(
            conversation, "Low health score", "system"
        )

    # 6. Persist updates
    await conversation_repository.update(conversation)

    return conversation, bot_message
```

---

## 📊 **PERFORMANCE CONSIDERATIONS**

### **1. Entity Loading**
```python
# ❌ N+1 Problem
for conversation in conversations:
    bot = await bot_repository.get_by_id(conversation.bot_id)

# ✅ Batch Loading
bot_ids = [c.bot_id for c in conversations]
bots = await bot_repository.get_by_ids(bot_ids)
```

### **2. Context Size Management**
```python
# ConversationContext automatically limits:
# - Intent history: Last 10 intents
# - System notes: Last 20 notes
# - Conversation summary: Max 1000 chars
```

### **3. Immutability Performance**
```python
# Value Objects use structural sharing where possible
# Large contexts use incremental updates
new_context = context.add_entity("product", "iPhone")  # Efficient
```

---

## 🧪 **TESTING GUIDELINES**

### **1. Unit Tests - Domain Logic**
```python
def test_bot_cannot_handle_conversation_when_overloaded():
    bot = create_test_bot(
        max_concurrent_conversations=2,
        active_conversations=2
    )

    assert not bot.can_handle_new_conversation()

def test_conversation_auto_timeout():
    conversation = create_test_conversation(
        max_idle_minutes=15,
        last_activity=datetime.utcnow() - timedelta(minutes=20)
    )

    assert conversation.is_timed_out()
```

### **2. Business Rule Testing**
```python
def test_start_conversation_validates_external_user():
    orchestrator = ConversationOrchestrator()

    with pytest.raises(BusinessRuleViolationError, match="INVALID_EXTERNAL_USER_ID"):
        orchestrator.start_conversation(
            bot=bot,
            initial_message="Hello",
            external_user_id="",  # Invalid
            platform="telegram"
        )
```

---

## 🔮 **FUTURE EXTENSIONS**

### **1. Multi-Bot Conversations**
```python
# Support for bot handoffs
conversation = orchestrator.transfer_conversation(
    conversation=conversation,
    target_bot=specialist_bot,
    reason="Requires specialized knowledge"
)
```

### **2. Advanced Context Features**
```python
# Long-term memory across conversations
context = context.add_long_term_memory(
    key="user_preference",
    value="prefers_email_responses"
)

# Cross-conversation analytics
context = context.add_user_journey_step("checkout_initiated")
```

### **3. Enhanced Business Rules**
```python
# Dynamic rule engine
bot.add_business_rule(
    name="vip_priority",
    condition=lambda ctx: ctx.external_user_data.get("is_vip"),
    action=lambda conv: conv.escalate_priority(Priority.HIGH, "VIP user")
)
```

---

## 📚 **ADDITIONAL RESOURCES**

- 📖 **Domain-Driven Design**: Evans, Eric
- 🏛️ **Clean Architecture**: Martin, Robert C.
- 🔄 **Event Sourcing**: Fowler, Martin
- 🎯 **CQRS Pattern**: Young, Greg

---

**💡 Tip**: Domain Layer là foundation của toàn bộ hệ thống. Hãy đầu tư thời gian hiểu rõ business rules và maintain high code quality ở layer này!