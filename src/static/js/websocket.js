/**
 * WebSocket module
 * Handles WebSocket connection and message routing
 */

/**
 * Connect to the WebSocket server and handle incoming messages
 */
function connect() {
    // Use wss:// if page is https://, otherwise ws://
    // This enables secure WebSocket when behind HTTPS/reverse proxy
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.hostname}:${DefaultConfig.API_PORT}${ApiEndpoint.WEBSOCKET}`);

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        // Handle typed messages (event-driven updates)
        if (msg.type) {
            switch (msg.type) {
                case MessageType.INITIAL:
                    // Initial full state - process all data
                    if (msg.sensor_status) window.sensorStatus = msg.sensor_status;
                    window.updateSensors(msg.sensors);
                    window.updateWeather(msg.weather);
                    window.updateNameday(msg.nameday);
                    window.updateHealth(msg.health);
                    window.updateSystem(msg.system);
                    window.updateTransport(msg.transport);
                    window.updateSensorStatusIndicators();
                    if (msg.todoist) TodoistManager.update(msg.todoist);
                    break;
                case MessageType.SENSORS:
                    window.updateSensors(msg.data);
                    break;
                case MessageType.SENSOR_STATUS:
                    window.sensorStatus = msg.data;
                    window.updateSensorStatusIndicators();
                    break;
                case MessageType.WEATHER:
                    window.updateWeather(msg.data);
                    break;
                case MessageType.NAMEDAY:
                    window.updateNameday(msg.data);
                    break;
                case MessageType.SYSTEM:
                    window.updateSystem(msg.data);
                    break;
                case MessageType.TRANSPORT:
                    window.updateTransport(msg.data);
                    break;
                case MessageType.TODOIST:
                    TodoistManager.update(msg.data);
                    break;
                case MessageType.HEARTBEAT:
                    // Keep-alive, nothing to do
                    break;
                default:
                    console.log('Unknown message type:', msg.type);
            }
            return;
        }

        // Legacy: handle old format (all data in one object) for backwards compatibility
        if (msg.sensors) window.updateSensors(msg.sensors);
        if (msg.weather) window.updateWeather(msg.weather);
        if (msg.nameday) window.updateNameday(msg.nameday);
        if (msg.health) window.updateHealth(msg.health);
        if (msg.system) window.updateSystem(msg.system);
        if (msg.transport) window.updateTransport(msg.transport);
    };

    ws.onclose = () => setTimeout(connect, Interval.WEBSOCKET_RECONNECT);
}

// Export for use in other modules
window.connect = connect;
