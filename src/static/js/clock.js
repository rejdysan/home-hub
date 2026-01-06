/**
 * Clock functionality module
 * Handles time and date display updates
 */

/**
 * Updates the clock time and date display
 */
function updateClock() {
    const now = new Date();
    const isNightMode = window.getCurrentMode && window.getCurrentMode() === KioskMode.NIGHT;

    // In night mode show HH:MM only, otherwise show HH:MM:SS
    const timeFormat = isNightMode
        ? {hour: '2-digit', minute: '2-digit'}
        : {hour: '2-digit', minute: '2-digit', second: '2-digit'};

    document.getElementById(ElementId.CLOCK_TIME).innerText = now.toLocaleTimeString(Locale.TIME, timeFormat);
    document.getElementById(ElementId.CLOCK_DATE).innerText = now.toLocaleDateString(Locale.DATE, DateFormat.FULL_DATE);
}

// Export for use in other modules
window.updateClock = updateClock;

