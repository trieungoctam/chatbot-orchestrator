class AdminApp {
    constructor() {
        this.config = {
            apiEndpoint: 'http://localhost:8000',
            apiKey: '',
            currentSection: 'dashboard'
        };

        this.elements = {};
        this.charts = {};
        this.refreshIntervals = {};

        this.init();
    }

    init() {
        this.bindElements();
        this.loadSettings();
        this.bindEvents();
        this.showSection('dashboard');
        this.startAutoRefresh();
    }

    bindElements() {
        // Navigation elements
        this.elements.navItems = document.querySelectorAll('.nav-item');
        this.elements.sectionTitle = document.getElementById('sectionTitle');
        this.elements.sections = document.querySelectorAll('.content-section');
        this.elements.sidebarToggle = document.getElementById('sidebarToggle');
        this.elements.backToChatBtn = document.getElementById('backToChatBtn');

        // Dashboard elements
        this.elements.refreshDashboard = document.getElementById('refreshDashboard');
        this.elements.totalConversations = document.getElementById('totalConversations');
        this.elements.activeBots = document.getElementById('activeBots');
        this.elements.dailyMessages = document.getElementById('dailyMessages');
        this.elements.systemUptime = document.getElementById('systemUptime');
        this.elements.activityList = document.getElementById('activityList');
        this.elements.systemStatus = document.getElementById('systemStatus');

        // Bot management elements
        this.elements.createBotBtn = document.getElementById('createBotBtn');
        this.elements.botsTableBody = document.getElementById('botsTableBody');

        // Bot form elements
        this.elements.botName = document.getElementById('botName');
        this.elements.botDescription = document.getElementById('botDescription');
        this.elements.botLanguage = document.getElementById('botLanguage');
        this.elements.botCoreAI = document.getElementById('botCoreAI');
        this.elements.botPlatform = document.getElementById('botPlatform');
        this.elements.botPrompt = document.getElementById('botPrompt');

        // Conversation elements
        this.elements.conversationsTableBody = document.getElementById('conversationsTableBody');
        this.elements.conversationSearch = document.getElementById('conversationSearch');
        this.elements.conversationFilter = document.getElementById('conversationFilter');

        // Platform elements
        this.elements.platformsTableBody = document.getElementById('platformsTableBody');
        this.elements.createPlatformBtn = document.getElementById('createPlatformBtn');

        // Core AI elements
        this.elements.coreAIsTableBody = document.getElementById('coreAIsTableBody');
        this.elements.createCoreAIBtn = document.getElementById('createCoreAIBtn');

        // Modal elements
        this.elements.createBotModal = document.getElementById('createBotModal');
        this.elements.closeBotModalBtn = document.getElementById('closeBotModalBtn');
        this.elements.cancelBotBtn = document.getElementById('cancelBotBtn');
        this.elements.createBotForm = document.getElementById('createBotForm');

        // Loading overlay
        this.elements.loadingOverlay = document.getElementById('loadingOverlay');
    }

    bindEvents() {
        // Navigation events
        this.elements.navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.getAttribute('data-section');
                this.showSection(section);
            });
        });

        // Dashboard events
        if (this.elements.refreshDashboard) {
            this.elements.refreshDashboard.addEventListener('click', () => this.loadDashboard());
        }

        // Bot management events
        if (this.elements.createBotBtn) {
            this.elements.createBotBtn.addEventListener('click', () => this.showCreateBotModal());
        }

        // Modal events
        if (this.elements.closeBotModalBtn) {
            this.elements.closeBotModalBtn.addEventListener('click', () => this.hideCreateBotModal());
        }
        if (this.elements.cancelBotBtn) {
            this.elements.cancelBotBtn.addEventListener('click', () => this.hideCreateBotModal());
        }
        if (this.elements.createBotForm) {
            this.elements.createBotForm.addEventListener('submit', (e) => this.handleCreateBot(e));
        }

        // Search and filter events
        if (this.elements.conversationSearch) {
            this.elements.conversationSearch.addEventListener('input', () => this.filterConversations());
        }
        if (this.elements.conversationFilter) {
            this.elements.conversationFilter.addEventListener('change', () => this.filterConversations());
        }

        // Other events
        if (this.elements.sidebarToggle) {
            this.elements.sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }
        if (this.elements.backToChatBtn) {
            this.elements.backToChatBtn.addEventListener('click', () => window.open('index.html', '_blank'));
        }
    }

    async showSection(sectionName) {
        this.config.currentSection = sectionName;

        // Update navigation
        this.elements.navItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('data-section') === sectionName) {
                item.classList.add('active');
            }
        });

        // Update sections
        this.elements.sections.forEach(section => {
            section.classList.remove('active');
            if (section.id === sectionName) {
                section.classList.add('active');
            }
        });

        // Update title
        const titles = {
            dashboard: 'Dashboard',
            bots: 'Bot Management',
            conversations: 'Conversations',
            'core-ai': 'Core AI Management',
            platforms: 'Platforms',
            monitoring: 'Monitoring',
            settings: 'Settings',
            logs: 'System Logs'
        };
        this.elements.sectionTitle.textContent = titles[sectionName] || sectionName;

        // Load section data
        await this.loadSectionData(sectionName);
    }

    async loadSectionData(sectionName) {
        try {
            switch (sectionName) {
                case 'dashboard':
                    await this.loadDashboard();
                    break;
                case 'bots':
                    await this.loadBots();
                    break;
                case 'conversations':
                    await this.loadConversations();
                    break;
                case 'platforms':
                    await this.loadPlatforms();
                    break;
                case 'core-ai':
                    await this.loadCoreAI(); // Core AI section now uses 'core-ai' instead of 'users'
                    break;
                case 'monitoring':
                    await this.loadMonitoring();
                    break;
                case 'logs':
                    await this.loadLogs();
                    break;
            }
        } catch (error) {
            console.error(`Error loading ${sectionName}:`, error);
            this.showErrorMessage(`Failed to load ${sectionName} data`);
        }
    }

    async loadDashboard() {
        try {
            this.showLoading();

            // Load dashboard statistics from real APIs
            const [botStats, conversationStats, coreAiStats, platformStats] = await Promise.all([
                this.apiCall('/api/v1/admin/bot/stats/total'),
                this.apiCall('/api/v1/admin/conversation/stats/total'),
                this.apiCall('/api/v1/admin/core-ai/stats/total'),
                this.apiCall('/api/v1/admin/platform/stats/total')
            ]);

            // Update dashboard metrics
            if (conversationStats.success) {
                this.elements.totalConversations.textContent = conversationStats.data.total_conversations || 0;
                this.elements.dailyMessages.textContent = conversationStats.data.messages_today || 0;
            }

            if (botStats.success) {
                this.elements.activeBots.textContent = botStats.data.active_bots || 0;
            }

            // Update system uptime (mock for now)
            this.elements.systemUptime.textContent = this.calculateUptime();

            // Load recent activity
            await this.loadRecentActivity();

            // Update system status
            this.updateSystemStatus();

            // Load charts if not already loaded
            this.loadDashboardCharts();

        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showErrorMessage('Failed to load dashboard data');
        } finally {
            this.hideLoading();
        }
    }

    async loadBots() {
        try {
            this.showLoading();

            const response = await this.apiCall('/api/v1/admin/bot/');

            if (response.success && response.data) {
                this.renderBotsTable(response.data);
            } else {
                this.showErrorMessage('Failed to load bots');
            }
        } catch (error) {
            console.error('Error loading bots:', error);
            this.showErrorMessage('Failed to load bots');
        } finally {
            this.hideLoading();
        }
    }

    renderBotsTable(bots) {
        if (!this.elements.botsTableBody) return;

        this.elements.botsTableBody.innerHTML = '';

        bots.forEach(bot => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${bot.id}</td>
                <td>${bot.name}</td>
                <td>${bot.core_ai?.name || 'N/A'}</td>
                <td>${bot.platform?.name || 'N/A'}</td>
                <td>${bot.language || 'N/A'}</td>
                <td>
                    <span class="status-badge ${bot.is_active ? 'active' : 'inactive'}">
                        ${bot.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>${this.formatDate(bot.created_at)}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="adminApp.editBot('${bot.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="adminApp.toggleBotStatus('${bot.id}', ${bot.is_active})" title="${bot.is_active ? 'Deactivate' : 'Activate'}">
                        <i class="fas fa-${bot.is_active ? 'pause' : 'play'}"></i>
                    </button>
                    <button class="btn-icon" onclick="adminApp.deleteBot('${bot.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            this.elements.botsTableBody.appendChild(row);
        });
    }

    async loadConversations() {
        try {
            this.showLoading();

            const response = await this.apiCall('/api/v1/admin/conversation/');

            if (response.success && response.data) {
                this.renderConversationsTable(response.data);
            } else {
                this.showErrorMessage('Failed to load conversations');
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
            this.showErrorMessage('Failed to load conversations');
        } finally {
            this.hideLoading();
        }
    }

    renderConversationsTable(conversations) {
        if (!this.elements.conversationsTableBody) return;

        this.elements.conversationsTableBody.innerHTML = '';

        conversations.forEach(conversation => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${conversation.id}</td>
                <td>${conversation.bot_id || 'N/A'}</td>
                <td>${conversation.message_count || 0}</td>
                <td>
                    <span class="status-badge ${conversation.status}">
                        ${conversation.status}
                    </span>
                </td>
                <td>${this.formatDate(conversation.created_at)}</td>
                <td>${this.formatDate(conversation.updated_at)}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="adminApp.viewConversation('${conversation.id}')" title="View">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon" onclick="adminApp.endConversation('${conversation.id}')" title="End">
                        <i class="fas fa-stop"></i>
                    </button>
                    <button class="btn-icon" onclick="adminApp.deleteConversation('${conversation.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            this.elements.conversationsTableBody.appendChild(row);
        });
    }

    async loadRecentActivity() {
        try {
            // Load recent conversations as activity
            const response = await this.apiCall('/api/v1/admin/conversation/?limit=5');

            if (response.success && response.data) {
                this.renderActivityList(response.data);
            }
        } catch (error) {
            console.error('Error loading recent activity:', error);
        }
    }

    renderActivityList(conversations) {
        if (!this.elements.activityList) return;

        this.elements.activityList.innerHTML = '';

        conversations.slice(0, 5).forEach(conversation => {
            const item = document.createElement('div');
            item.className = 'activity-item';
            item.innerHTML = `
                <div class="activity-icon">
                    <i class="fas fa-comment"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">New conversation started</div>
                    <div class="activity-time">${this.timeAgo(conversation.created_at)}</div>
                </div>
            `;
            this.elements.activityList.appendChild(item);
        });
    }

    // Bot Management Methods
    async showCreateBotModal() {
        if (this.elements.createBotModal) {
            // Clear form
            this.elements.createBotForm.reset();

            // Load Core AI options
            await this.loadCoreAIOptions();

            // Load Platform options
            await this.loadPlatformOptions();

            // Show modal
            this.elements.createBotModal.classList.add('show');
        }
    }

    async loadCoreAIOptions() {
        try {
            const response = await this.apiCall('/api/v1/admin/core-ai/active');

            if (response.success && response.data) {
                this.elements.botCoreAI.innerHTML = '<option value="">Select Core AI...</option>';
                response.data.forEach(coreAI => {
                    const option = document.createElement('option');
                    option.value = coreAI.id;
                    option.textContent = coreAI.name;
                    this.elements.botCoreAI.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading Core AI options:', error);
            this.showErrorMessage('Failed to load Core AI options');
        }
    }

    async loadPlatformOptions() {
        try {
            const response = await this.apiCall('/api/v1/admin/platform/');

            if (response.success && response.data) {
                // Filter active platforms
                const activePlatforms = response.data.filter(platform => platform.is_active);

                this.elements.botPlatform.innerHTML = '<option value="">Select Platform...</option>';
                activePlatforms.forEach(platform => {
                    const option = document.createElement('option');
                    option.value = platform.id;
                    option.textContent = platform.name;
                    this.elements.botPlatform.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading Platform options:', error);
            this.showErrorMessage('Failed to load Platform options');
        }
    }

    hideCreateBotModal() {
        if (this.elements.createBotModal) {
            this.elements.createBotModal.classList.remove('show');
        }
    }

    async handleCreateBot(e) {
        e.preventDefault();

        try {
            this.showLoading();

            // Collect form data properly
            const botData = {
                name: this.elements.botName.value.trim(),
                description: this.elements.botDescription.value.trim() || null,
                language: this.elements.botLanguage.value,
                core_ai_id: this.elements.botCoreAI.value,
                platform_id: this.elements.botPlatform.value,
                system_prompt: this.elements.botPrompt.value.trim() || 'You are a helpful AI assistant.',
                context_config: {},
                is_active: true
            };

            // Validation
            if (!botData.name) {
                this.showErrorMessage('Bot name is required');
                return;
            }

            if (!botData.core_ai_id) {
                this.showErrorMessage('Please select a Core AI');
                return;
            }

            if (!botData.platform_id) {
                this.showErrorMessage('Please select a Platform');
                return;
            }

            // Call bot API
            const response = await this.apiCall('/api/v1/admin/bot/', 'POST', botData);

            if (response.success) {
                this.hideCreateBotModal();
                this.showSuccessMessage('Bot created successfully');
                await this.loadBots(); // Refresh the bots list
            } else {
                // Handle API error response
                const errorMessage = response.detail || response.message || 'Failed to create bot';
                this.showErrorMessage(errorMessage);
            }
        } catch (error) {
            console.error('Error creating bot:', error);
            this.showErrorMessage('Failed to create bot: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async toggleBotStatus(botId, currentStatus) {
        try {
            const action = currentStatus ? 'deactivate' : 'activate';
            const response = await this.apiCall(`/api/v1/admin/bot/${botId}/${action}`, 'POST');

            if (response.success) {
                this.showSuccessMessage(`Bot ${action}d successfully`);
                await this.loadBots(); // Refresh the bots list
            } else {
                this.showErrorMessage(`Failed to ${action} bot`);
            }
        } catch (error) {
            console.error(`Error ${currentStatus ? 'deactivating' : 'activating'} bot:`, error);
            this.showErrorMessage('Failed to update bot status');
        }
    }

    async deleteBot(botId) {
        if (!confirm('Are you sure you want to delete this bot? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await this.apiCall(`/api/v1/admin/bot/${botId}`, 'DELETE');

            if (response.success) {
                this.showSuccessMessage('Bot deleted successfully');
                await this.loadBots(); // Refresh the bots list
            } else {
                this.showErrorMessage('Failed to delete bot');
            }
        } catch (error) {
            console.error('Error deleting bot:', error);
            this.showErrorMessage('Failed to delete bot');
        }
    }

    // Conversation Management Methods
    async endConversation(conversationId) {
        if (!confirm('Are you sure you want to end this conversation?')) {
            return;
        }

        try {
            const response = await this.apiCall(`/api/v1/admin/conversation/${conversationId}/end`, 'POST');

            if (response.success) {
                this.showSuccessMessage('Conversation ended successfully');
                await this.loadConversations();
            } else {
                this.showErrorMessage('Failed to end conversation');
            }
        } catch (error) {
            console.error('Error ending conversation:', error);
            this.showErrorMessage('Failed to end conversation');
        }
    }

    async deleteConversation(conversationId) {
        if (!confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await this.apiCall(`/api/v1/admin/conversation/${conversationId}`, 'DELETE');

            if (response.success) {
                this.showSuccessMessage('Conversation deleted successfully');
                await this.loadConversations();
            } else {
                this.showErrorMessage('Failed to delete conversation');
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
            this.showErrorMessage('Failed to delete conversation');
        }
    }

    async viewConversation(conversationId) {
        try {
            const response = await this.apiCall(`/api/v1/admin/conversation/${conversationId}/messages`);

            if (response.success) {
                // Create a simple modal to show conversation details
                const modal = this.createConversationModal(conversationId, response.data);
                document.body.appendChild(modal);
            } else {
                this.showErrorMessage('Failed to load conversation details');
            }
        } catch (error) {
            console.error('Error viewing conversation:', error);
            this.showErrorMessage('Failed to load conversation details');
        }
    }

    createConversationModal(conversationId, messages) {
        const modal = document.createElement('div');
        modal.className = 'modal show';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Conversation Details</h3>
                    <button class="btn-close" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body" style="max-height: 400px; overflow-y: auto;">
                    <h4>Conversation ID: ${conversationId}</h4>
                    <div class="messages-list">
                        ${messages.map(msg => `
                            <div class="message-item" style="margin-bottom: 10px; padding: 10px; border-left: 3px solid ${msg.message_role === 'user' ? '#007bff' : '#28a745'};">
                                <strong>${msg.message_role}:</strong> ${msg.content}
                                <div style="font-size: 0.8em; color: #666; margin-top: 5px;">
                                    ${this.formatDate(msg.created_at)}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
                </div>
            </div>
        `;
        return modal;
    }

    // Platform Management Methods
    async loadPlatforms() {
        try {
            this.showLoading();

            const response = await this.apiCall('/api/v1/admin/platform/');

            if (response.success && response.data) {
                this.renderPlatformsTable(response.data);
            } else {
                this.showErrorMessage('Failed to load platforms');
            }
        } catch (error) {
            console.error('Error loading platforms:', error);
            this.showErrorMessage('Failed to load platforms');
        } finally {
            this.hideLoading();
        }
    }

    renderPlatformsTable(platforms) {
        if (!this.elements.platformsTableBody) return;

        this.elements.platformsTableBody.innerHTML = '';

        platforms.forEach(platform => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${platform.id}</td>
                <td>${platform.name}</td>
                <td>${platform.base_url || 'N/A'}</td>
                <td>
                    <span class="status-badge ${platform.is_active ? 'active' : 'inactive'}">
                        ${platform.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>${this.formatDate(platform.created_at)}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="adminApp.editPlatform('${platform.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="adminApp.togglePlatformStatus('${platform.id}', ${platform.is_active})" title="${platform.is_active ? 'Deactivate' : 'Activate'}">
                        <i class="fas fa-${platform.is_active ? 'pause' : 'play'}"></i>
                    </button>
                    <button class="btn-icon" onclick="adminApp.deletePlatform('${platform.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            this.elements.platformsTableBody.appendChild(row);
        });
    }

    async togglePlatformStatus(platformId, currentStatus) {
        try {
            const action = currentStatus ? 'deactivate' : 'activate';
            const response = await this.apiCall(`/api/v1/admin/platform/${platformId}/${action}`, 'POST');

            if (response.success) {
                this.showSuccessMessage(`Platform ${action}d successfully`);
                await this.loadPlatforms(); // Refresh the platforms list
            } else {
                this.showErrorMessage(`Failed to ${action} platform`);
            }
        } catch (error) {
            console.error(`Error ${currentStatus ? 'deactivating' : 'activating'} platform:`, error);
            this.showErrorMessage('Failed to update platform status');
        }
    }

    async deletePlatform(platformId) {
        if (!confirm('Are you sure you want to delete this platform? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await this.apiCall(`/api/v1/admin/platform/${platformId}`, 'DELETE');

            if (response.success) {
                this.showSuccessMessage('Platform deleted successfully');
                await this.loadPlatforms(); // Refresh the platforms list
            } else {
                this.showErrorMessage('Failed to delete platform');
            }
        } catch (error) {
            console.error('Error deleting platform:', error);
            this.showErrorMessage('Failed to delete platform');
        }
    }

    async editPlatform(platformId) {
        // For now, just show a message. You can implement a modal later
        this.showSuccessMessage(`Edit platform ${platformId} - Feature coming soon`);
    }

    // Core AI Management Methods
    async loadCoreAI() {
        try {
            this.showLoading();

            const response = await this.apiCall('/api/v1/admin/core-ai/');

            if (response.success && response.data) {
                this.renderCoreAITable(response.data);
            } else {
                this.showErrorMessage('Failed to load Core AI');
            }
        } catch (error) {
            console.error('Error loading Core AI:', error);
            this.showErrorMessage('Failed to load Core AI');
        } finally {
            this.hideLoading();
        }
    }

    renderCoreAITable(coreAIs) {
        if (!this.elements.coreAIsTableBody) return;

        this.elements.coreAIsTableBody.innerHTML = '';

        coreAIs.forEach(coreAI => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${coreAI.id}</td>
                <td>${coreAI.name}</td>
                <td>${coreAI.api_endpoint || 'N/A'}</td>
                <td>${coreAI.model_name || 'N/A'}</td>
                <td>
                    <span class="status-badge ${coreAI.is_active ? 'active' : 'inactive'}">
                        ${coreAI.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>${this.formatDate(coreAI.created_at)}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="adminApp.editCoreAI('${coreAI.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="adminApp.toggleCoreAIStatus('${coreAI.id}', ${coreAI.is_active})" title="${coreAI.is_active ? 'Deactivate' : 'Activate'}">
                        <i class="fas fa-${coreAI.is_active ? 'pause' : 'play'}"></i>
                    </button>
                    <button class="btn-icon" onclick="adminApp.deleteCoreAI('${coreAI.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            this.elements.coreAIsTableBody.appendChild(row);
        });
    }

    async toggleCoreAIStatus(coreAIId, currentStatus) {
        try {
            const action = currentStatus ? 'deactivate' : 'activate';
            const response = await this.apiCall(`/api/v1/admin/core-ai/${coreAIId}/${action}`, 'POST');

            if (response.success) {
                this.showSuccessMessage(`Core AI ${action}d successfully`);
                await this.loadCoreAI(); // Refresh the Core AI list
            } else {
                this.showErrorMessage(`Failed to ${action} Core AI`);
            }
        } catch (error) {
            console.error(`Error ${currentStatus ? 'deactivating' : 'activating'} Core AI:`, error);
            this.showErrorMessage('Failed to update Core AI status');
        }
    }

    async deleteCoreAI(coreAIId) {
        if (!confirm('Are you sure you want to delete this Core AI? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await this.apiCall(`/api/v1/admin/core-ai/${coreAIId}`, 'DELETE');

            if (response.success) {
                this.showSuccessMessage('Core AI deleted successfully');
                await this.loadCoreAI(); // Refresh the Core AI list
            } else {
                this.showErrorMessage('Failed to delete Core AI');
            }
        } catch (error) {
            console.error('Error deleting Core AI:', error);
            this.showErrorMessage('Failed to delete Core AI');
        }
    }

    async editCoreAI(coreAIId) {
        // For now, just show a message. You can implement a modal later
        this.showSuccessMessage(`Edit Core AI ${coreAIId} - Feature coming soon`);
    }

    // Monitoring and Charts
    loadDashboardCharts() {
        if (!window.Chart) return;

        // Message Volume Chart
        const messageCtx = document.getElementById('messageChart');
        if (messageCtx && !this.charts.messageChart) {
            this.charts.messageChart = new Chart(messageCtx, {
                type: 'line',
                data: {
                    labels: this.generateTimeLabels(24),
                    datasets: [{
                        label: 'Messages',
                        data: this.generateMockData(24, 0, 50),
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // Performance Chart
        const performanceCtx = document.getElementById('performanceChart');
        if (performanceCtx && !this.charts.performanceChart) {
            this.charts.performanceChart = new Chart(performanceCtx, {
                type: 'line',
                data: {
                    labels: this.generateTimeLabels(24),
                    datasets: [{
                        label: 'Response Time (ms)',
                        data: this.generateMockData(24, 50, 200),
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // Error Chart
        const errorCtx = document.getElementById('errorChart');
        if (errorCtx && !this.charts.errorChart) {
            this.charts.errorChart = new Chart(errorCtx, {
                type: 'bar',
                data: {
                    labels: this.generateTimeLabels(24),
                    datasets: [{
                        label: 'Errors',
                        data: this.generateMockData(24, 0, 5),
                        backgroundColor: 'rgba(220, 53, 69, 0.8)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    }

    async loadMonitoring() {
        this.loadDashboardCharts();
    }

    async loadLogs() {
        // Mock logs for now - you can integrate with real logging system later
        const logViewer = document.getElementById('logViewer');
        if (logViewer) {
            logViewer.innerHTML = `
                <div class="log-entry info">
                    <span class="log-time">${new Date().toISOString()}</span>
                    <span class="log-level">INFO</span>
                    <span class="log-message">System started successfully</span>
                </div>
                <div class="log-entry info">
                    <span class="log-time">${new Date(Date.now() - 60000).toISOString()}</span>
                    <span class="log-level">INFO</span>
                    <span class="log-message">Bot created: default-bot</span>
                </div>
                <div class="log-entry warning">
                    <span class="log-time">${new Date(Date.now() - 120000).toISOString()}</span>
                    <span class="log-level">WARNING</span>
                    <span class="log-message">High memory usage detected</span>
                </div>
            `;
        }
    }

    // Utility Methods
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

    filterConversations() {
        // Implement conversation filtering based on search and filter inputs
        // This would filter the displayed table rows
    }

    calculateUptime() {
        // Mock uptime calculation
        return '24h 30m';
    }

    updateSystemStatus() {
        if (this.elements.systemStatus) {
            this.elements.systemStatus.innerHTML = `
                <span class="status-indicator online"></span>
                <span>System Online</span>
            `;
        }
    }

    generateTimeLabels(hours) {
        const labels = [];
        for (let i = hours - 1; i >= 0; i--) {
            const time = new Date(Date.now() - i * 60 * 60 * 1000);
            labels.push(time.getHours() + ':00');
        }
        return labels;
    }

    generateMockData(count, min, max) {
        return Array.from({ length: count }, () =>
            Math.floor(Math.random() * (max - min + 1)) + min
        );
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString() + ' ' +
               new Date(dateString).toLocaleTimeString();
    }

    timeAgo(dateString) {
        const now = new Date();
        const date = new Date(dateString);
        const diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) return `${diffInSeconds} seconds ago`;
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        return `${Math.floor(diffInSeconds / 86400)} days ago`;
    }

    showLoading() {
        if (this.elements.loadingOverlay) {
            this.elements.loadingOverlay.classList.add('show');
        }
    }

    hideLoading() {
        if (this.elements.loadingOverlay) {
            this.elements.loadingOverlay.classList.remove('show');
        }
    }

    showSuccessMessage(message) {
        this.showNotification(message, 'success');
    }

    showErrorMessage(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007bff'};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            z-index: 10000;
            font-weight: 500;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    toggleSidebar() {
        document.querySelector('.admin-container').classList.toggle('sidebar-collapsed');
    }

    startAutoRefresh() {
        // Auto-refresh dashboard every 30 seconds
        this.refreshIntervals.dashboard = setInterval(() => {
            if (this.config.currentSection === 'dashboard') {
                this.loadDashboard();
            }
        }, 30000);

        // Auto-refresh conversations every 60 seconds
        this.refreshIntervals.conversations = setInterval(() => {
            if (this.config.currentSection === 'conversations') {
                this.loadConversations();
            }
        }, 60000);
    }

    loadSettings() {
        const saved = localStorage.getItem('admin_config');
        if (saved) {
            const savedConfig = JSON.parse(saved);
            this.config = { ...this.config, ...savedConfig };
        }
    }

    saveSettings() {
        localStorage.setItem('admin_config', JSON.stringify(this.config));
    }
}

// Initialize the admin app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.adminApp = new AdminApp();
});