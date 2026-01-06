/**
 * Clock functionality module
 * Handles time and date display updates
 */

/**
 * Updates the clock time and date display
 */
function updateClock() {
    const now = new Date();

    // Check if we're in night mode
    const isNightMode = window.getCurrentMode && window.getCurrentMode() === window.KioskMode.NIGHT;

    // Format time based on mode (manual formatting for better browser compatibility)
    let timeString;
    if (isNightMode) {
        // Night mode: HH:MM only
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        timeString = `${hours}:${minutes}`;
    } else {
        // Day/Morning mode: HH:MM:SS
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        timeString = `${hours}:${minutes}:${seconds}`;
    }

    document.getElementById(ElementId.CLOCK_TIME).innerText = timeString;
    document.getElementById(ElementId.CLOCK_DATE).innerText = now.toLocaleDateString(Locale.DATE, DateFormat.FULL_DATE);
}

// Export for use in other modules
window.updateClock = updateClock;

