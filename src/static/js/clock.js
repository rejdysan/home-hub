/**
 * Clock functionality module
 * Handles time and date display updates
 */

/**
 * Updates the clock time and date display
 */
function updateClock() {
    const now = new Date();
    document.getElementById(ElementId.CLOCK_TIME).innerText = now.toLocaleTimeString(Locale.TIME);
    document.getElementById(ElementId.CLOCK_DATE).innerText = now.toLocaleDateString(Locale.DATE, DateFormat.FULL_DATE);
}

// Export for use in other modules
window.updateClock = updateClock;

