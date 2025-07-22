// QUANTUM-PCI Web Interface JavaScript

const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'],
    data() {
        return {
            // Connection status
            connectionStatus: false,
            websocket: null,
            
            // Loading states
            loading: false,
            
            // Device data
            deviceInfo: null,
            healthStatus: null,
            smaConfig: null,
            
            // Form data
            selectedClockSource: '',
            
            // Monitoring
            monitoringActive: false,
            monitoringData: [],
            
            // Notifications
            notification: null,
            
            // API base URL
            apiBase: window.location.origin + '/api'
        }
    },
    
    async mounted() {
        console.log('QUANTUM-PCI Web Interface v2.0 - Starting...');
        
        // Initialize the interface
        await this.initialize();
        
        // Setup WebSocket connection
        this.setupWebSocket();
        
        // Periodic refresh
        setInterval(() => {
            if (this.connectionStatus && !this.loading) {
                this.refreshData();
            }
        }, 30000); // Refresh every 30 seconds
    },
    
    beforeUnmount() {
        if (this.websocket) {
            this.websocket.close();
        }
    },
    
    methods: {
        async initialize() {
            console.log('Initializing interface...');
            
            // Check API health
            try {
                const response = await axios.get(`${this.apiBase}/health`);
                this.connectionStatus = response.data.device_available;
                console.log('API Health:', response.data);
                
                if (this.connectionStatus) {
                    await this.loadInitialData();
                }
            } catch (error) {
                console.error('Failed to connect to API:', error);
                this.showNotification('Ошибка подключения к API', 'error');
            }
        },
        
        async loadInitialData() {
            console.log('Loading initial data...');
            this.loading = true;
            
            try {
                // Load device info, health status, and SMA config in parallel
                const [deviceResponse, statusResponse, smaResponse] = await Promise.all([
                    axios.get(`${this.apiBase}/device/info`),
                    axios.get(`${this.apiBase}/device/status`),
                    axios.get(`${this.apiBase}/device/sma-config`)
                ]);
                
                this.deviceInfo = deviceResponse.data;
                this.healthStatus = statusResponse.data.health_status;
                this.smaConfig = smaResponse.data;
                
                // Set default clock source
                this.selectedClockSource = this.deviceInfo.current_clock_source;
                
                console.log('Initial data loaded successfully');
            } catch (error) {
                console.error('Failed to load initial data:', error);
                this.showNotification('Ошибка загрузки данных устройства', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        setupWebSocket() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
            
            console.log('Connecting to WebSocket:', wsUrl);
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.connectionStatus = true;
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.connectionStatus = false;
                
                // Try to reconnect after 5 seconds
                setTimeout(() => {
                    if (!this.connectionStatus) {
                        console.log('Attempting to reconnect...');
                        this.setupWebSocket();
                    }
                }, 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.connectionStatus = false;
            };
        },
        
        handleWebSocketMessage(data) {
            console.log('WebSocket message:', data);
            
            switch (data.type) {
                case 'status_update':
                    if (data.data && typeof data.data.health !== 'undefined') {
                        if (this.healthStatus) {
                            this.healthStatus.healthy = data.data.health;
                        }
                    }
                    break;
                    
                case 'clock_source_changed':
                    this.showNotification(`Источник синхронизации изменен на ${data.source}`, 'success');
                    if (this.deviceInfo) {
                        this.deviceInfo.current_clock_source = data.source;
                        this.selectedClockSource = data.source;
                    }
                    break;
                    
                case 'sma_input_changed':
                    this.showNotification(`SMA${data.port} вход настроен на ${data.signal}`, 'success');
                    break;
                    
                case 'sma_output_changed':
                    this.showNotification(`SMA${data.port} выход настроен на ${data.signal}`, 'success');
                    break;
                    
                case 'monitoring_update':
                    if (this.monitoringActive) {
                        this.addMonitoringEntry('system_update', 'Обновление статуса системы', data.timestamp);
                    }
                    break;
                    
                default:
                    console.log('Unknown WebSocket message type:', data.type);
            }
        },
        
        async refreshDeviceInfo() {
            console.log('Refreshing device info...');
            this.loading = true;
            
            try {
                const response = await axios.get(`${this.apiBase}/device/info`);
                this.deviceInfo = response.data;
                this.selectedClockSource = this.deviceInfo.current_clock_source;
                this.showNotification('Информация об устройстве обновлена', 'success');
            } catch (error) {
                console.error('Failed to refresh device info:', error);
                this.showNotification('Ошибка обновления информации', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        async refreshData() {
            try {
                const [statusResponse, smaResponse] = await Promise.all([
                    axios.get(`${this.apiBase}/device/status`),
                    axios.get(`${this.apiBase}/device/sma-config`)
                ]);
                
                this.healthStatus = statusResponse.data.health_status;
                this.smaConfig = smaResponse.data;
                
                console.log('Data refreshed');
            } catch (error) {
                console.error('Failed to refresh data:', error);
            }
        },
        
        async setClockSource() {
            if (!this.selectedClockSource) {
                this.showNotification('Выберите источник синхронизации', 'error');
                return;
            }
            
            console.log('Setting clock source to:', this.selectedClockSource);
            this.loading = true;
            
            try {
                await axios.post(`${this.apiBase}/device/clock-source`, {
                    source: this.selectedClockSource
                });
                
                // Success message will be handled by WebSocket
                console.log('Clock source set successfully');
            } catch (error) {
                console.error('Failed to set clock source:', error);
                this.showNotification('Ошибка установки источника синхронизации', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        async setSMAInput(port, signal) {
            const portNumber = parseInt(port.replace('sma', ''));
            console.log(`Setting SMA${portNumber} input to:`, signal);
            
            try {
                await axios.post(`${this.apiBase}/device/sma-input`, {
                    port: portNumber,
                    signal: signal
                });
                
                // Success message will be handled by WebSocket
                console.log('SMA input set successfully');
            } catch (error) {
                console.error('Failed to set SMA input:', error);
                this.showNotification('Ошибка настройки SMA входа', 'error');
            }
        },
        
        async setSMAOutput(port, signal) {
            const portNumber = parseInt(port.replace('sma', ''));
            console.log(`Setting SMA${portNumber} output to:`, signal);
            
            try {
                await axios.post(`${this.apiBase}/device/sma-output`, {
                    port: portNumber,
                    signal: signal
                });
                
                // Success message will be handled by WebSocket
                console.log('SMA output set successfully');
            } catch (error) {
                console.error('Failed to set SMA output:', error);
                this.showNotification('Ошибка настройки SMA выхода', 'error');
            }
        },
        
        toggleMonitoring() {
            this.monitoringActive = !this.monitoringActive;
            
            if (this.monitoringActive) {
                this.addMonitoringEntry('system', 'Мониторинг запущен');
                console.log('Monitoring started');
            } else {
                this.addMonitoringEntry('system', 'Мониторинг остановлен');
                console.log('Monitoring stopped');
            }
        },
        
        addMonitoringEntry(type, message, timestamp = null) {
            if (!this.monitoringActive && type !== 'system') {
                return;
            }
            
            const entry = {
                type: type,
                message: message,
                timestamp: timestamp || new Date().toISOString()
            };
            
            this.monitoringData.push(entry);
            
            // Keep only last 100 entries
            if (this.monitoringData.length > 100) {
                this.monitoringData = this.monitoringData.slice(-100);
            }
        },
        
        showNotification(message, type = 'success') {
            this.notification = {
                message: message,
                type: type
            };
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                this.notification = null;
            }, 5000);
        },
        
        formatTime(timestamp) {
            if (!timestamp) return '';
            
            try {
                const date = new Date(timestamp);
                return date.toLocaleString('ru-RU', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
            } catch (error) {
                return timestamp;
            }
        },
        
        formatCheckName(checkName) {
            const translations = {
                'device_accessible': 'Доступность устройства',
                'gnss_sync': 'GNSS синхронизация',
                'clock_stability': 'Стабильность часов',
                'sma_connectivity': 'Подключение SMA',
                'health_checks': 'Проверки состояния',
                'system_health': 'Состояние системы'
            };
            
            return translations[checkName] || checkName;
        }
    }
}).mount('#app');