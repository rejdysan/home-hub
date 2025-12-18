/**
 * Main Application Entry Point
 * Initializes all modules and starts the dashboard
 *
 * Module dependencies (loaded before this file):
 * - constants.js: Enums and constants
 * - clock.js: Clock functionality
 * - iframe.js: Iframe refresh helpers
 * - weather.js: Weather icon mapping and background
 * - transport.js: Bus list rendering
 * - updates.js: UI update functions
 * - websocket.js: WebSocket connection handling
 * - kiosk.js: Kiosk mode management
 */

console.log('🚀 app.js loaded at', new Date().toISOString());

/**
 * Initialize the application
 * Sets up intervals and fetches configuration
 */
function initializeApp() {
    // Start clock updates
    setInterval(window.updateClock, Interval.CLOCK_UPDATE);
    window.updateClock();

    // Check kiosk mode every second for quick transitions
    setInterval(window.applyKioskMode, Interval.KIOSK_CHECK);

    // Fetch config and set up dynamic refresh intervals
    fetchConfigAndSetupIntervals();

    // Start WebSocket connection
    window.connect();
}

/**
 * Fetch configuration from API and set up refresh intervals
 */
function fetchConfigAndSetupIntervals() {
    const apiBase = `http://${window.location.hostname}:${DefaultConfig.API_PORT}`;
    console.log('🔄 Fetching config from', apiBase + ApiEndpoint.CONFIG);

    fetch(apiBase + ApiEndpoint.CONFIG)
        .then(response => {
            console.log('📡 Config response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(cfg => {
            console.log('📋 Raw config received:', cfg);

            // Set kiosk config
            window.kioskConfig.morning_mode_start = cfg.morning_mode_start || DefaultConfig.MORNING_MODE_START;
            window.kioskConfig.day_mode_start = cfg.day_mode_start || DefaultConfig.DAY_MODE_START;
            window.kioskConfig.night_mode_start = cfg.night_mode_start || DefaultConfig.NIGHT_MODE_START;
            console.log('🎛️ Kiosk config loaded:', window.kioskConfig);
            console.log('🕐 Current mode:', window.getCurrentMode());

            // Apply kiosk mode immediately
            window.applyKioskMode();

            // Update timestamps on initial load
            const now = new Date();
            const timestamp = "Updated: " + now.toLocaleTimeString(Locale.TIME);
            document.getElementById(ElementId.UPDATE_MAP_1).innerText = timestamp;
            document.getElementById(ElementId.UPDATE_MAP_2).innerText = timestamp;
            document.getElementById(ElementId.UPDATE_CAL_1).innerText = timestamp;
            document.getElementById(ElementId.UPDATE_CAL_2).innerText = timestamp;

            // Set up separate refresh intervals
            setInterval(window.refreshMaps, cfg.google_maps_update_interval);
            setInterval(window.refreshCalendar, cfg.google_calendar_update_interval);
            console.log(`Maps refresh: ${cfg.google_maps_update_interval / 1000}s, Calendar refresh: ${cfg.google_calendar_update_interval / 1000}s`);
        })
        .catch(err => {
            // Fallback to defaults if config fetch fails
            console.error('❌ Failed to fetch config:', err);
            window.applyKioskMode();
            setInterval(window.refreshMaps, Interval.DEFAULT_MAP_REFRESH);
            setInterval(window.refreshCalendar, Interval.DEFAULT_CALENDAR_REFRESH);
        });
}

// Start the application
initializeApp();
