/**
 * Iframe refresh module
 * Handles refreshing of embedded iframes (maps, calendars)
 */

/**
 * Refresh an iframe without the blank-page blink.
 *
 * Double-buffered: a hidden clone loads the same src behind the visible
 * frame; once loaded (plus a grace period for map tiles to paint) it
 * cross-fades in and replaces the old frame. The old map stays visible
 * for the entire reload, so nothing ever flashes white.
 *
 * @param {string} id - The iframe element ID
 */
function hardRefreshIframe(id) {
    const frame = document.getElementById(id);
    if (!frame) return;

    const container = frame.parentElement;
    // Drop any stale buffer from a refresh that never finished (e.g. offline)
    container.querySelectorAll('.iframe-buffer').forEach(b => b.remove());

    const src = frame.getAttribute('src');
    const buffer = frame.cloneNode(false);
    buffer.removeAttribute('id');
    buffer.removeAttribute('src'); // set after wiring the load handler
    buffer.classList.add('iframe-buffer');

    buffer.addEventListener('load', () => {
        // Give the freshly loaded map a moment to paint its tiles,
        // then cross-fade and promote the buffer to be the real frame
        setTimeout(() => {
            buffer.classList.add('iframe-buffer-visible');
            setTimeout(() => {
                frame.remove();
                buffer.id = id;
                buffer.classList.remove('iframe-buffer', 'iframe-buffer-visible');
            }, 700); // matches the CSS opacity transition
        }, 900);
    }, { once: true });

    container.appendChild(buffer);
    buffer.src = src;
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
