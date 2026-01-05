/**
 * Kiosk mode module
 * Handles display mode switching based on time of day
 */

// Kiosk mode configuration (will be set from API)
window.kioskConfig = {
    morning_mode_start: DefaultConfig.MORNING_MODE_START,
    day_mode_start: DefaultConfig.DAY_MODE_START,
    night_mode_start: DefaultConfig.NIGHT_MODE_START
};

// Current active mode
let currentMode = null;

/**
 * Parse time string to minutes since midnight
 * @param {string} timeStr - Time string in HH:MM format
 * @returns {number} Minutes since midnight
 */
function parseTime(timeStr) {
    const [hours, minutes] = timeStr.split(':').map(Number);
    return hours * 60 + minutes;
}

/**
 * Get current kiosk mode based on time
 * @returns {string} Current mode: 'morning', 'day', or 'night'
 */
function getCurrentMode() {
    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();

    const morningStart = parseTime(window.kioskConfig.morning_mode_start);
    const dayStart = parseTime(window.kioskConfig.day_mode_start);
    const nightStart = parseTime(window.kioskConfig.night_mode_start);

    if (currentTime >= nightStart || currentTime < morningStart) {
        return KioskMode.NIGHT;
    } else if (currentTime >= dayStart) {
        return KioskMode.DAY;
    } else {
        return KioskMode.MORNING;
    }
}

/**
 * Apply kiosk mode based on current time
 * Adjusts visibility of UI elements based on mode
 */
function applyKioskMode() {
    const mode = getCurrentMode();

    // Only update if mode changed
    if (mode === currentMode) return;
    currentMode = mode;

    const body = document.body;
    const topContainer = document.querySelector(Selector.TOP_CONTAINER);
    const bottomContainer = document.querySelector(Selector.BOTTOM_CONTAINER);
    const mapRects = document.querySelectorAll(Selector.MAP_RECTS);
    const clockRect = document.querySelector(Selector.CLOCK_RECT);
    const otherBottomRects = document.querySelectorAll(Selector.OTHER_BOTTOM_RECTS);

    // Reset ALL styles first
    body.classList.remove(CssClass.NIGHT_MODE);
    if (topContainer) {
        topContainer.style.display = '';
        topContainer.style.gridTemplateColumns = '';
    }
    if (bottomContainer) {
        bottomContainer.style.display = '';
    }
    mapRects.forEach(el => el.style.display = '');
    otherBottomRects.forEach(el => el.style.display = '');
    if (clockRect) clockRect.classList.remove(CssClass.NIGHT_MODE_CLOCK);

    if (mode === KioskMode.MORNING) {
        // Show everything (default)
        console.log('🌅 Morning mode: Full dashboard');
    } else if (mode === KioskMode.DAY) {
        // Hide maps, show only calendars (each taking half width)
        console.log('☀️ Day mode: Calendars only');
        mapRects.forEach(el => el.style.display = 'none');
        if (topContainer) {
            topContainer.style.gridTemplateColumns = '1fr 1fr';
        }
    } else if (mode === KioskMode.NIGHT) {
        // Show only clock on black background
        console.log('🌙 Night mode: Clock only');
        body.classList.add(CssClass.NIGHT_MODE);
        if (topContainer) topContainer.style.display = 'none';
        // Hide all bottom container children except clock
        otherBottomRects.forEach(el => el.style.display = 'none');
        if (clockRect) clockRect.classList.add(CssClass.NIGHT_MODE_CLOCK);
    }
}

// Export for use in other modules
window.getCurrentMode = getCurrentMode;
window.applyKioskMode = applyKioskMode;

