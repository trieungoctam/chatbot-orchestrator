class ChatApp {
    constructor() {
        this.config = {
            apiEndpoint: 'http://localhost:8000',
            apiKey: '',
            currentConversationId: null,
            currentBotId: 'default-bot',
            conversations: [],
            settings: {
                autoScroll: true,
                soundNotifications: false,
                theme: 'light'
            }
        };

        this.contextLimits = {
            conservative: { max_messages: 10, max_chars: 5000 },
            standard: { max_messages: 20, max_chars: 10000 },
            extended: { max_messages: 50, max_chars: 25000 },
            maximum: { max_messages: 100, max_chars: 50000 }
        };

        this.elements = {};
        this.isLoading = false;

        this.init();
    }

    async init() {
        this.bindElements();
        this.bindEvents();
        this.loadSettings();
        this.initializeChat();

        // Load available bots from API
        await this.loadAvailableBots();

        // Load conversations and other data
        this.loadConversations();
    }

    bindElements() {
        this.elements = {
            // Header elements
            settingsBtn: document.getElementById('settingsBtn'),
            adminBtn: document.getElementById('adminBtn'),

            // Sidebar elements
            newChatBtn: document.getElementById('newChatBtn'),
            conversationList: document.getElementById('conversationList'),
            contextPreset: document.getElementById('contextPreset'),
            contextInfo: document.getElementById('contextInfo'),

            // Chat elements
            chatTitle: document.getElementById('chatTitle'),
            chatStatus: document.getElementById('chatStatus'),
            messagesContainer: document.getElementById('messagesContainer'),
            exportBtn: document.getElementById('exportBtn'),
            clearBtn: document.getElementById('clearBtn'),

            // Input elements
            messageForm: document.getElementById('messageForm'),
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            charCount: document.getElementById('charCount'),
            botSelect: document.getElementById('botSelect'),

            // Modal elements
            settingsModal: document.getElementById('settingsModal'),
            closeSettingsBtn: document.getElementById('closeSettingsBtn'),
            apiEndpoint: document.getElementById('apiEndpoint'),
            apiKey: document.getElementById('apiKey'),
            autoScroll: document.getElementById('autoScroll'),
            soundNotifications: document.getElementById('soundNotifications'),
            theme: document.getElementById('theme'),
            resetSettingsBtn: document.getElementById('resetSettingsBtn'),
            saveSettingsBtn: document.getElementById('saveSettingsBtn'),

            // Loading overlay
            loadingOverlay: document.getElementById('loadingOverlay')
        };
    }

    bindEvents() {
        // Header events
        this.elements.settingsBtn.addEventListener('click', () => this.openSettings());
        this.elements.adminBtn.addEventListener('click', () => this.openAdmin());

        // Sidebar events
        this.elements.newChatBtn.addEventListener('click', () => this.startNewConversation());
        this.elements.contextPreset.addEventListener('change', () => this.updateContextInfo());

        // Chat events
        this.elements.exportBtn.addEventListener('click', () => this.exportConversation());
        this.elements.clearBtn.addEventListener('click', () => this.clearConversation());

        // Input events
        this.elements.messageForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.elements.messageInput.addEventListener('input', () => {
            this.updateCharCount();
            this.updateSendButton();
        });
        this.elements.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSubmit(e);
            }
        });
        this.elements.botSelect.addEventListener('change', () => this.handleBotChange());

        // Modal events
        this.elements.closeSettingsBtn.addEventListener('click', () => this.closeSettings());
        this.elements.saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        this.elements.resetSettingsBtn.addEventListener('click', () => this.resetSettings());

        // Quick action events
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-action-btn')) {
                const message = e.target.getAttribute('data-message');
                this.sendQuickMessage(message);
            }
        });

        // Close modal on backdrop click
        this.elements.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.elements.settingsModal) {
                this.closeSettings();
            }
        });
    }

    setupAutoResize() {
        const textarea = this.elements.messageInput;
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        });
    }

    loadContextLimits() {
        this.updateContextInfo();
    }

    updateContextInfo() {
        const preset = this.elements.contextPreset.value;
        const limits = this.contextLimits[preset];
        this.elements.contextInfo.textContent = `Max ${limits.max_messages} messages, ${limits.max_chars.toLocaleString()} chars`;
    }

    async loadBots() {
        try {
            // Try to load bots from API
            const response = await this.apiCall('/api/v1/bots', 'GET');
            if (response.success && response.data) {
                this.populateBotSelector(response.data);
            }
        } catch (error) {
            console.log('Could not load bots from API, using default');
            // Keep default bot
        }
    }

    populateBotSelector(bots) {
        this.elements.botSelect.innerHTML = '';

        if (bots.length === 0) {
            // No bots available
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No bots available';
            this.elements.botSelect.appendChild(option);
            this.config.currentBotId = '';
            this.updateChatStatus('No bots available');
            return;
        }

        bots.forEach(bot => {
            const option = document.createElement('option');
            option.value = bot.id;
            option.textContent = `${bot.name} (${bot.language || 'vi'})`;
            this.elements.botSelect.appendChild(option);
        });

        // Set first bot as default
        this.config.currentBotId = bots[0].id;
        this.elements.botSelect.value = bots[0].id;

        this.updateChatStatus(`Bot selected: ${bots[0].name}`);
    }

    handleInputChange() {
        const text = this.elements.messageInput.value;
        const length = text.length;

        this.elements.charCount.textContent = length;
        this.elements.sendBtn.disabled = length === 0 || this.isLoading;

        // Change color based on length
        if (length > 1800) {
            this.elements.charCount.style.color = 'var(--error-color)';
        } else if (length > 1500) {
            this.elements.charCount.style.color = 'var(--warning-color)';
        } else {
            this.elements.charCount.style.color = 'var(--gray-500)';
        }
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!this.elements.sendBtn.disabled) {
                this.handleSubmit(e);
            }
        }
    }

    handleBotChange() {
        this.config.currentBotId = this.elements.botSelect.value;
        this.updateChatStatus(`Bot changed to ${this.elements.botSelect.options[this.elements.botSelect.selectedIndex].text}`);
    }

    async handleSubmit(e) {
        e.preventDefault();

        const message = this.elements.messageInput.value.trim();
        if (!message || this.isLoading) return;

        await this.sendMessage(message);
    }

    async sendQuickMessage(message) {
        this.elements.messageInput.value = message;
        this.handleInputChange();
        await this.sendMessage(message);
    }

    async sendMessage(messageContent) {
        if (!messageContent.trim()) return;

        // Validate bot selection
        if (!this.config.currentBotId || this.config.currentBotId === 'default-bot') {
            this.addMessage('bot', 'Please select a valid bot from the dropdown before sending messages.', 'error');
            return;
        }

        try {
            this.showLoading();

            // Add user message to UI
            this.addMessage('user', messageContent);

            // Get current conversation history in the correct format
            const history = this.formatHistoryForAPI();

            // Prepare request payload according to PancakeMessageRequest schema
            const requestPayload = {
                conversation_id: this.config.currentConversationId,
                bot_id: this.config.currentBotId,
                history: history,
                resources: {
                    user_id: 'web_user',
                    session_type: 'web',
                    device: 'desktop',
                    context: {
                        location: 'chat_interface',
                        timestamp: new Date().toISOString()
                    }
                }
            };

            console.log('Sending message request:', requestPayload);

            // Call chat API
            const response = await fetch(`${this.config.apiEndpoint}/api/v1/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
                },
                body: JSON.stringify(requestPayload)
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Chat API response:', result);

            // Visualize response
            this.visualizeResponse(result);

            // Handle successful response
            if (result.success) {
                this.handleSuccessfulResponse(result);
            } else {
                this.handleErrorResponse(result);
            }

            // Clear input
            this.elements.messageInput.value = '';
            this.updateCharCount();
            this.updateSendButton();

        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('bot', `Error: ${error.message}`, 'error');
            this.updateChatStatus('Error sending message');
        } finally {
            this.hideLoading();
        }
    }

    formatHistoryForAPI() {
        // Convert conversation history to the required string format
        // Format: <USER>message</USER><br><BOT>response</BOT><br>
        const conversation = this.config.conversations.find(c => c.id === this.config.currentConversationId);
        const messages = conversation?.messages || [];

        let historyString = '';
        messages.forEach(message => {
            const role = message.type.toUpperCase();
            historyString += `<${role}>${message.content}</${role}><br>`;
        });

        return historyString;
    }

    visualizeResponse(response) {
        // Add a special message to visualize the API response
        const visualizationData = {
            success: response.success,
            status: response.status,
            action: response.action,
            ai_job_id: response.ai_job_id,
            lock_id: response.lock_id,
            consolidated_messages: response.consolidated_messages,
            bot_name: response.bot_name,
            consolidated_count: response.consolidated_count,
            cancelled_previous_job: response.cancelled_previous_job,
            reprocessing: response.reprocessing,
            lock_updated: response.lock_updated,
            context_limit: response.context_limit
        };

        // Create visualization message
        const visualDiv = document.createElement('div');
        visualDiv.className = 'response-visualization';
        visualDiv.innerHTML = `
            <div class="api-response-details">
                <h4><i class="fas fa-info-circle"></i> API Response Details</h4>
                <div class="response-grid">
                    <div class="response-item">
                        <strong>Status:</strong>
                        <span class="status-badge ${response.success ? 'success' : 'error'}">
                            ${response.status}
                        </span>
                    </div>
                    ${response.action ? `<div class="response-item"><strong>Action:</strong> ${response.action}</div>` : ''}
                    ${response.ai_job_id ? `<div class="response-item"><strong>AI Job ID:</strong> <code>${response.ai_job_id}</code></div>` : ''}
                    ${response.lock_id ? `<div class="response-item"><strong>Lock ID:</strong> <code>${response.lock_id}</code></div>` : ''}
                    ${response.bot_name ? `<div class="response-item"><strong>Bot:</strong> ${response.bot_name}</div>` : ''}
                    ${response.consolidated_messages ? `<div class="response-item"><strong>Consolidated Messages:</strong> ${response.consolidated_messages}</div>` : ''}
                    ${response.reprocessing ? `<div class="response-item"><strong>Reprocessing:</strong> Yes</div>` : ''}
                    ${response.lock_updated ? `<div class="response-item"><strong>Lock Updated:</strong> Yes</div>` : ''}
                </div>
                <details class="raw-response">
                    <summary>Raw Response Data</summary>
                    <pre><code>${JSON.stringify(response, null, 2)}</code></pre>
                </details>
            </div>
        `;

        // Add visualization to chat
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        messageDiv.appendChild(visualDiv);

        this.elements.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    handleSuccessfulResponse(response) {
        // Update conversation ID if it was generated
        if (response.conversation_id && !this.config.currentConversationId) {
            this.config.currentConversationId = response.conversation_id;
        }

        // Add bot response message if available
        if (response.message) {
            this.addMessage('bot', response.message);
        }

        // Update chat status based on response
        let statusMessage = `Status: ${response.status}`;
        if (response.bot_name) {
            statusMessage += ` | Bot: ${response.bot_name}`;
        }
        if (response.action) {
            statusMessage += ` | Action: ${response.action}`;
        }

        this.updateChatStatus(statusMessage);
    }

    handleErrorResponse(response) {
        const errorMessage = response.error || response.message || 'Unknown error occurred';
        this.addMessage('bot', errorMessage, 'error');
        this.updateChatStatus(`Error: ${response.status}`);
    }

    addMessageToUI(type, content) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = type === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        messageText.textContent = content;

        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = new Date().toLocaleTimeString();

        messageContent.appendChild(messageText);
        messageContent.appendChild(messageTime);

        if (type === 'user') {
            messageElement.appendChild(messageContent);
            messageElement.appendChild(avatar);
        } else {
            messageElement.appendChild(avatar);
            messageElement.appendChild(messageContent);
        }

        // Remove welcome message if it exists
        const welcomeMessage = this.elements.messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        this.elements.messagesContainer.appendChild(messageElement);

        // Update conversation in memory
        this.updateConversationMessages(type, content);

        if (this.config.settings.autoScroll) {
            this.scrollToBottom();
        }
    }

    addErrorMessage(message) {
        const errorElement = document.createElement('div');
        errorElement.className = 'message assistant error';
        errorElement.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="message-content" style="background-color: var(--error-color); color: white;">
                <div class="message-text">${message}</div>
                <div class="message-time">${new Date().toLocaleTimeString()}</div>
            </div>
        `;

        this.elements.messagesContainer.appendChild(errorElement);

        if (this.config.settings.autoScroll) {
            this.scrollToBottom();
        }
    }

    scrollToBottom() {
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
    }

    updateConversationMessages(type, content) {
        const conversation = this.config.conversations.find(c => c.id === this.config.currentConversationId);
        if (conversation) {
            conversation.messages.push({
                type: type,
                content: content,
                timestamp: new Date().toISOString()
            });
            conversation.lastMessage = content.substring(0, 100);
            conversation.updatedAt = new Date().toISOString();
            this.saveConversations();
            this.renderConversationList();
        }
    }

    validateConversationId(id) {
        // Check if ID is valid UUID format
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
        if (!uuidRegex.test(id)) {
            return false;
        }

        // Check if ID is unique
        return !this.config.conversations.some(conv => conv.id === id);
    }

    setCustomConversationId(customId) {
        if (!customId) {
            return this.generateUUID();
        }

        if (this.validateConversationId(customId)) {
            return customId;
        } else {
            console.warn('Invalid or duplicate conversation ID. Generating new UUID instead.');
            return this.generateUUID();
        }
    }

    startNewConversation(customId = null) {
        const conversationId = this.setCustomConversationId(customId);
        const botName = this.elements.botSelect.options[this.elements.botSelect.selectedIndex].text;

        const newConversation = {
            id: conversationId,
            title: `New ${botName} Chat`,
            messages: [],
            lastMessage: '',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            botId: this.config.currentBotId
        };

        this.config.conversations.unshift(newConversation);
        this.config.currentConversationId = conversationId;

        this.saveConversations();
        this.renderConversationList();
        this.clearMessages();
        this.updateChatTitle(newConversation.title);
        this.updateChatStatus(`Ready (ID: ${conversationId})`);

        return conversationId;
    }

    clearMessages() {
        this.elements.messagesContainer.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <i class="fas fa-comments"></i>
                </div>
                <h3>Welcome to AI Chat Assistant</h3>
                <p>I'm here to help with your questions and provide assistance. How can I help you today?</p>
                <div class="quick-actions">
                    <button class="quick-action-btn" data-message="Hello! Can you help me with something?">
                        <i class="fas fa-hand-wave"></i>
                        Say Hello
                    </button>
                    <button class="quick-action-btn" data-message="What can you do for me?">
                        <i class="fas fa-question-circle"></i>
                        What can you do?
                    </button>
                    <button class="quick-action-btn" data-message="Can you explain how this works?">
                        <i class="fas fa-info-circle"></i>
                        How it works
                    </button>
                </div>
            </div>
        `;
    }

    loadConversations() {
        const saved = localStorage.getItem('chat_conversations');
        if (saved) {
            this.config.conversations = JSON.parse(saved);
        }
        this.renderConversationList();
    }

    saveConversations() {
        localStorage.setItem('chat_conversations', JSON.stringify(this.config.conversations));
    }

    renderConversationList() {
        const list = this.elements.conversationList;
        list.innerHTML = '';

        this.config.conversations.forEach(conversation => {
            const item = document.createElement('div');
            item.className = 'conversation-item';
            if (conversation.id === this.config.currentConversationId) {
                item.classList.add('active');
            }

            item.innerHTML = `
                <div class="conversation-title">${conversation.title}</div>
                <div class="conversation-preview">${conversation.lastMessage || 'No messages yet'}</div>
            `;

            item.addEventListener('click', () => this.loadConversation(conversation.id));
            list.appendChild(item);
        });
    }

    loadConversation(conversationId) {
        const conversation = this.config.conversations.find(c => c.id === conversationId);
        if (!conversation) return;

        this.config.currentConversationId = conversationId;
        this.clearMessages();

        // Load messages
        conversation.messages.forEach(message => {
            this.addMessageToUI(message.type, message.content);
        });

        this.updateChatTitle(conversation.title);
        this.renderConversationList();
    }

    getCurrentConversation() {
        return this.config.conversations.find(c => c.id === this.config.currentConversationId);
    }

    clearConversation() {
        if (!this.config.currentConversationId) return;

        if (confirm('Are you sure you want to clear this conversation? This action cannot be undone.')) {
            const conversation = this.getCurrentConversation();
            if (conversation) {
                conversation.messages = [];
                conversation.lastMessage = '';
                this.saveConversations();
                this.clearMessages();
                this.renderConversationList();
            }
        }
    }

    exportConversation() {
        const conversation = this.getCurrentConversation();
        if (!conversation || conversation.messages.length === 0) {
            alert('No conversation to export.');
            return;
        }

        const content = conversation.messages.map(msg =>
            `${msg.type.toUpperCase()}: ${msg.content}`
        ).join('\n\n');

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat_${conversation.id}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }

    updateChatTitle(title) {
        this.elements.chatTitle.textContent = title;
    }

    updateChatStatus(status) {
        this.elements.chatStatus.textContent = status;
    }

    showLoading() {
        this.isLoading = true;
        this.elements.loadingOverlay.classList.add('show');
        this.updateSendButton();
    }

    hideLoading() {
        this.isLoading = false;
        this.elements.loadingOverlay.classList.remove('show');
        this.updateSendButton();
    }

    openSettings() {
        this.elements.settingsModal.classList.add('show');
        this.loadSettingsToModal();
    }

    closeSettings() {
        this.elements.settingsModal.classList.remove('show');
    }

    openAdmin() {
        window.open('admin.html', '_blank');
    }

    loadSettingsToModal() {
        this.elements.apiEndpoint.value = this.config.apiEndpoint;
        this.elements.apiKey.value = this.config.apiKey;
        this.elements.autoScroll.checked = this.config.settings.autoScroll;
        this.elements.soundNotifications.checked = this.config.settings.soundNotifications;
        this.elements.theme.value = this.config.settings.theme;
    }

    saveSettings() {
        this.config.apiEndpoint = this.elements.apiEndpoint.value || 'http://localhost:8000';
        this.config.apiKey = this.elements.apiKey.value;
        this.config.settings.autoScroll = this.elements.autoScroll.checked;
        this.config.settings.soundNotifications = this.elements.soundNotifications.checked;
        this.config.settings.theme = this.elements.theme.value;

        localStorage.setItem('chat_config', JSON.stringify(this.config));
        this.closeSettings();
        this.showNotification('Settings saved successfully!');
    }

    resetSettings() {
        if (confirm('Are you sure you want to reset all settings to default?')) {
            this.config = {
                ...this.config,
                apiEndpoint: 'http://localhost:8000',
                apiKey: '',
                settings: {
                    autoScroll: true,
                    soundNotifications: false,
                    theme: 'light'
                }
            };
            localStorage.removeItem('chat_config');
            this.loadSettingsToModal();
            this.showNotification('Settings reset to default!');
        }
    }

    loadSettings() {
        const saved = localStorage.getItem('chat_config');
        if (saved) {
            const savedConfig = JSON.parse(saved);
            this.config = { ...this.config, ...savedConfig };
        }
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        const url = `${this.config.apiEndpoint}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json'
        };

        if (this.config.apiKey) {
            headers['X-API-KEY'] = this.config.apiKey;
        }

        const options = {
            method,
            headers
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`API call failed: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--success-color);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            z-index: 10000;
            font-weight: 500;
            box-shadow: var(--shadow-lg);
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    playNotificationSound() {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = 800;
        oscillator.type = 'sine';

        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    async loadAvailableBots() {
        try {
            // Load active bots from admin API
            const response = await fetch(`${this.config.apiEndpoint}/api/v1/admin/bot/active`);

            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    this.populateBotSelector(result.data);
                    this.updateChatStatus(`Loaded ${result.data.length} available bots`);
                } else {
                    // Fallback to all bots if active endpoint fails
                    await this.loadAllBots();
                }
            } else {
                // Fallback to default bot
                console.warn('Failed to load bots, using default');
                this.populateBotSelector([{
                    id: 'default-bot',
                    name: 'Default Bot'
                }]);
            }
        } catch (error) {
            console.error('Error loading bots:', error);
            this.populateBotSelector([{
                id: 'default-bot',
                name: 'Default Bot'
            }]);
        }
    }

    async loadAllBots() {
        try {
            const response = await fetch(`${this.config.apiEndpoint}/api/v1/admin/bot/`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    // Filter active bots
                    const activeBots = result.data.filter(bot => bot.is_active);
                    this.populateBotSelector(activeBots);
                    this.updateChatStatus(`Loaded ${activeBots.length} bots`);
                }
            }
        } catch (error) {
            console.error('Error loading all bots:', error);
        }
    }

    addMessage(type, content, messageType = 'normal') {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type} ${messageType}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = type === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        messageText.textContent = content;

        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = new Date().toLocaleTimeString();

        messageContent.appendChild(messageText);
        messageContent.appendChild(messageTime);

        if (type === 'user') {
            messageElement.appendChild(messageContent);
            messageElement.appendChild(avatar);
        } else {
            messageElement.appendChild(avatar);
            messageElement.appendChild(messageContent);
        }

        // Remove welcome message if it exists
        const welcomeMessage = this.elements.messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        this.elements.messagesContainer.appendChild(messageElement);

        // Update conversation in memory
        this.updateConversationMessages(type, content);

        if (this.config.settings.autoScroll) {
            this.scrollToBottom();
        }
    }

    updateCharCount() {
        const text = this.elements.messageInput.value;
        const length = text.length;
        this.elements.charCount.textContent = length;

        // Change color based on length
        if (length > 1800) {
            this.elements.charCount.style.color = 'var(--error-color)';
        } else if (length > 1500) {
            this.elements.charCount.style.color = 'var(--warning-color)';
        } else {
            this.elements.charCount.style.color = '';
        }
    }

    updateSendButton() {
        const text = this.elements.messageInput.value;
        const isEmpty = text.trim().length === 0;
        this.elements.sendBtn.disabled = isEmpty || this.isLoading;
    }

    initializeChat() {
        this.loadConversations();
        if (this.config.conversations.length === 0) {
            this.startNewConversation();
        } else {
            this.config.currentConversationId = this.config.conversations[0].id;
            this.loadConversationMessages();
        }
    }

    loadConversationMessages() {
        const conversation = this.config.conversations.find(c => c.id === this.config.currentConversationId);
        if (conversation) {
            this.clearMessages();
            conversation.messages.forEach(msg => {
                this.addMessage(msg.type, msg.content);
            });
            this.updateChatTitle(conversation.title);
        }
    }

    updateConversationId(oldId, newId) {
        // Find the conversation
        const conversation = this.config.conversations.find(c => c.id === oldId);
        if (!conversation) {
            console.error('Conversation not found');
            return false;
        }

        // Validate new ID
        if (!this.validateConversationId(newId)) {
            console.error('Invalid or duplicate conversation ID');
            return false;
        }

        // Update the conversation ID
        conversation.id = newId;

        // If this was the current conversation, update currentConversationId
        if (this.config.currentConversationId === oldId) {
            this.config.currentConversationId = newId;
        }

        // Save and refresh UI
        this.saveConversations();
        this.renderConversationList();
        this.updateChatStatus(`Conversation ID updated to: ${newId}`);

        return true;
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});