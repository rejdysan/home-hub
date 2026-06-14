/**
 * Transport module
 * Handles rendering of bus/transport information
 */

/**
 * @typedef {Object} BusInfo
 * @property {string} line - Bus line number
 * @property {string} direction - Bus direction/destination
 * @property {number} mins - Minutes until arrival
 * @property {number} delay_seconds - Delay in seconds (positive = late, negative = early)
 * @property {string} time_predicted - Predicted arrival time
 * @property {string} time_scheduled - Scheduled arrival time
 */

/**
 * Get color for a bus line
 * @param {string} line - Bus line number
 * @returns {string} Hex color code
 */
function getLineColor(line) {
    return BusLineColors[line] || Color.BUS_LINE_DEFAULT;
}

/**
 * Format delay in seconds to Mm:SSs format
 * @param {number} totalSeconds - Delay in seconds
 * @returns {string} Formatted delay string
 */
function formatDelay(totalSeconds) {
    if (!totalSeconds) return '';
    const absSec = Math.abs(totalSeconds);
    const m = Math.floor(absSec / 60);
    const s = (absSec % 60).toString().padStart(2, '0');
    const sign = totalSeconds > 0 ? '+' : '-';
    return `${sign}${m}m:${s}s`;
}

/**
 * Get delay color and formatted string based on delay seconds
 * @param {number} delaySec - Delay in seconds
 * @returns {{color: string, text: string}} Delay color and formatted text
 */
function getDelayInfo(delaySec) {
    if (delaySec > 0) {
        return {
            color: Color.DELAY_LATE,
            text: `<span style="color:${Color.DELAY_LATE}; margin-left:4px;">(${formatDelay(delaySec)})</span>`
        };
    }
    if (delaySec < DefaultConfig.EARLY_THRESHOLD) {
        return {
            color: Color.DELAY_EARLY,
            text: `<span style="color:${Color.DELAY_EARLY}; margin-left:4px;">(${formatDelay(delaySec)})</span>`
        };
    }
    return { color: Color.DELAY_DEFAULT, text: '' };
}

/**
 * Render a single bus item HTML
 * @param {BusInfo} bus - Bus information object
 * @param {number} index - Slot index (drives staggered entrance animation)
 * @returns {string} HTML string for the bus item
 */
function renderBusItem(bus, index) {
    const busColor = getLineColor(bus.line);
    const isUrgent = bus.mins <= 1;
    const { color: predColor, text: delayStr } = getDelayInfo(bus.delay_seconds);
    const timeColor = bus.mins <= 5 ? Color.TIME_SOON : Color.TIME_LATER;
    const minsDisplay = bus.mins <= 1
        ? 'Now'
        : `${bus.mins}<span class="${CssClass.BUS_MINS_UNIT}">m</span>`;

    return `
        <div class="${CssClass.BUS_ITEM}" style="--i: ${index}; border-left-color: ${busColor};">
            <div class="${CssClass.BUS_LINE}" style="background: ${busColor};">${bus.line}</div>
            <div class="${CssClass.BUS_DIRECTION}">${bus.direction}</div>
            <div class="${CssClass.BUS_TIMES}">
                <div class="${CssClass.BUS_TIME_PREDICTED}" style="color: ${predColor};">
                    P: ${bus.time_predicted} ${delayStr}
                </div>
                <div class="${CssClass.BUS_TIME_SCHEDULED}">S: ${bus.time_scheduled}</div>
            </div>
            <div class="${CssClass.BUS_MINS} ${isUrgent ? CssClass.BUS_URGENT : ''}">
                <span class="${CssClass.BUS_MINS_VALUE}" style="color: ${timeColor};">
                    ${minsDisplay}
                </span>
            </div>
        </div>
    `;
}

/**
 * Render an empty bus slot placeholder
 * @param {number} index - Slot index (drives staggered entrance animation)
 * @returns {string} HTML string for empty slot
 */
function renderEmptySlot(index) {
    return `<div class="${CssClass.BUS_ITEM}" style="--i: ${index}; opacity: 0.2; border-left-color: ${Color.BUS_LINE_DEFAULT};">
        <div class="${CssClass.BUS_LINE}" style="background: ${Color.BUS_LINE_DEFAULT};">--</div>
        <div class="${CssClass.BUS_DIRECTION}">--</div>
        <div class="${CssClass.BUS_TIMES}"><div class="${CssClass.BUS_TIME_PREDICTED}">--:--:--</div></div>
        <div class="${CssClass.BUS_MINS}"><span class="${CssClass.BUS_MINS_VALUE}">--</span></div>
    </div>`;
}

/**
 * Stable identity for a departure (minutes/delay change between refreshes,
 * but line + direction + scheduled time identify "the same bus").
 * @param {BusInfo} bus
 * @returns {string}
 */
function busKey(bus) {
    return `${bus.line}|${bus.direction}|${bus.time_scheduled}`;
}

/**
 * Render a list of buses to a container element.
 *
 * Animation policy (deliberate — see dashboard UX):
 * - First render: staggered fade-in.
 * - Same buses, refreshed times: silent in-place update, NO animation.
 * - Earliest bus(es) departed: the whole list slides up one row per departed
 *   bus, and the rows that scrolled in at the bottom fade in.
 *
 * @param {BusInfo[]} buses - Array of bus objects
 * @param {string} elementId - Container element ID
 */
function renderBusList(buses, elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;

    if (!buses || buses.length === 0) {
        el.innerHTML = `<div class="${CssClass.BUS_NO_DATA}">No buses found</div>`;
        el._busKeys = [];
        return;
    }

    const shown = buses.slice(0, DefaultConfig.BUS_SLOTS);
    const newKeys = shown.map(busKey);
    const prevKeys = el._busKeys;

    // Decide the animation mode BEFORE rebuilding the DOM
    let mode = 'silent';
    let shiftRows = 0;
    if (!prevKeys || prevKeys.length === 0) {
        mode = 'initial';
    } else if (prevKeys[0] !== newKeys[0]) {
        const idx = prevKeys.indexOf(newKeys[0]);
        if (idx > 0) {
            mode = 'shift';       // top bus(es) departed, list moves up
            shiftRows = idx;
        } else {
            mode = 'initial';     // unrelated list (e.g. after data gap)
        }
    }

    // Row height for the slide distance (measure before the rebuild)
    const firstRow = el.firstElementChild;
    const listGap = 6; // matches .bus-list gap in CSS
    const rowHeight = firstRow ? firstRow.offsetHeight + listGap : 44;

    const slots = [];
    for (let i = 0; i < DefaultConfig.BUS_SLOTS; i++) {
        slots.push(shown[i] ? renderBusItem(shown[i], i) : renderEmptySlot(i));
    }
    el.innerHTML = slots.join('');
    el._busKeys = newKeys;

    const items = el.children;
    if (mode === 'initial') {
        for (const item of items) item.classList.add('bus-enter');
    } else if (mode === 'shift') {
        el.style.setProperty('--shift', `${shiftRows * rowHeight}px`);
        el.classList.remove('shift-up');
        void el.offsetWidth; // restart the animation
        el.classList.add('shift-up');
        // Rows that scrolled in at the bottom are new — fade them in
        for (let i = items.length - shiftRows; i < items.length; i++) {
            if (items[i]) items[i].classList.add('bus-enter');
        }
    }
    // mode === 'silent': times refreshed in place, no animation
}

// Export for use in other modules
globalThis.renderBusList = renderBusList;
