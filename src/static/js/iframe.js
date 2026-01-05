/**
 * Iframe refresh module
 * Handles refreshing of embedded iframes (maps, calendars)
 */

/**
 * Force refresh an iframe by resetting its src attribute
 * @param {string} id - The iframe element ID
 */
function hardRefreshIframe(id) {
    const frame = document.getElementById(id);
    if (frame) {
        const src = frame.getAttribute('src');
        frame.removeAttribute('src');
        frame.setAttribute('src', src);
    }
}

/**
 * Generate a timestamp string for display
 * @returns {string} Formatted timestamp
 */
function getTimestamp() {
    return "Updated: " + new Date().toLocaleTimeString(Locale.TIME);
}

/**
 * Refresh both map iframes and update their timestamps
 */
function refreshMaps() {
    const timestamp = getTimestamp();
    hardRefreshIframe(ElementId.MAP_FRAME_1);
    hardRefreshIframe(ElementId.MAP_FRAME_2);
    const map1Tag = document.getElementById(ElementId.UPDATE_MAP_1);
    const map2Tag = document.getElementById(ElementId.UPDATE_MAP_2);
    if (map1Tag) map1Tag.innerText = timestamp;
    if (map2Tag) map2Tag.innerText = timestamp;
}

/**
 * Refresh both calendar iframes and update their timestamps
 */
function refreshCalendar() {
    const timestamp = getTimestamp();
    hardRefreshIframe(ElementId.CALENDAR_FRAME_1);
    hardRefreshIframe(ElementId.CALENDAR_FRAME_2);
    const cal1Tag = document.getElementById(ElementId.UPDATE_CAL_1);
    const cal2Tag = document.getElementById(ElementId.UPDATE_CAL_2);
    if (cal1Tag) cal1Tag.innerText = timestamp;
    if (cal2Tag) cal2Tag.innerText = timestamp;
}

// Export for use in other modules
window.hardRefreshIframe = hardRefreshIframe;
window.refreshMaps = refreshMaps;
window.refreshCalendar = refreshCalendar;
