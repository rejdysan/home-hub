/**
 * Calendar module - Month-view grid replicating Google Calendar
 * Renders a traditional calendar grid with events overlaid on dates
 */

/**
 * Get the first day of a month (0 = Monday, 6 = Sunday)
 * JavaScript's getDay() returns 0 for Sunday, so we adjust to make Monday = 0
 * @param {number} year
 * @param {number} month (0-11)
 * @returns {number}
 */
function getFirstDayOfMonth(year, month) {
    const day = new Date(year, month, 1).getDay();
    // Convert: Sunday (0) -> 6, Monday (1) -> 0, Tuesday (2) -> 1, etc.
    return day === 0 ? 6 : day - 1;
}

/**
 * Get the number of days in a month
 * @param {number} year
 * @param {number} month (0-11)
 * @returns {number}
 */
function getDaysInMonth(year, month) {
    return new Date(year, month + 1, 0).getDate();
}

/**
 * Check if two dates are the same day
 * @param {Date} date1
 * @param {Date} date2
 * @returns {boolean}
 */
function isSameDay(date1, date2) {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
}

/**
 * Parse ISO date string to Date object
 * @param {string} isoString
 * @returns {Date}
 */
function parseEventDate(isoString) {
    if (!isoString) return new Date();
    try {
        return new Date(isoString);
    } catch (e) {
        console.error('Error parsing date:', e);
        return new Date();
    }
}

/**
 * Format time for event display (HH:MM)
 * @param {string} isoString
 * @param {boolean} allDay
 * @returns {string}
 */
function formatEventTime(isoString, allDay) {
    if (!isoString || allDay) return '';

    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        console.error('Error formatting event time:', e);
        return '';
    }
}

/**
 * Get calendar class based on calendar name
 * @param {string} calendarName
 * @returns {string}
 */
function getCalendarClass(calendarName) {
    if (calendarName && calendarName.toLowerCase().includes('rejdy')) {
        return CssClass.CALENDAR_EVENT_REJDY;
    } else if (calendarName && calendarName.toLowerCase().includes('zuz')) {
        return CssClass.CALENDAR_EVENT_ZUZ;
    } else if (calendarName && calendarName.toLowerCase().includes('czech')) {
        return CssClass.CALENDAR_EVENT_CZ;
    } else if (calendarName && calendarName.toLowerCase().includes('slovak')) {
        return CssClass.CALENDAR_EVENT_SK;
    }
    return '';
}

/**
 * Get date key in YYYY-MM-DD format
 * @param {Date} date
 * @returns {string}
 */
function getDateKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

/**
 * Calculate event duration in days
 * @param {Object} event
 * @returns {number}
 */
function getEventDurationDays(event) {
    const start = parseEventDate(event.start);
    const end = parseEventDate(event.end);

    // Normalize to start of day for comparison
    const startDay = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    const endDay = new Date(end.getFullYear(), end.getMonth(), end.getDate());

    const diffMs = endDay - startDay;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    // For all-day events, Google Calendar API returns exclusive end dates
    // For example, a 1-day event on Jan 5 has start=Jan 5, end=Jan 6
    // We need to subtract 1 to get the actual duration
    if (event.all_day && diffDays > 0) {
        return diffDays; // End is exclusive, so don't add 1
    }

    return Math.max(1, diffDays);
}

/**
 * Check if event is multi-day
 * @param {Object} event
 * @returns {boolean}
 */
function isMultiDayEvent(event) {
    return getEventDurationDays(event) > 1;
}

/**
 * Calculate compacted display rows for each cell based on multi-day events
 * @param {Array} multiDayEvents - Array of multi-day event segments with eventRow assigned
 * @param {Array} gridDates - Array of Date objects for each cell in the grid
 * @returns {Map} Map of cellIndex -> number of display rows needed
 */
function calculateDisplayRows(multiDayEvents, gridDates) {
    const cellDisplayRowCount = new Map();

    // Initialize all cells to 0
    for (let index = 0; index < gridDates.length; index++) {
        cellDisplayRowCount.set(index, 0);
    }

    // Group events by week
    const eventsByWeek = new Map();
    multiDayEvents.forEach(event => {
        if (!eventsByWeek.has(event.gridRow)) {
            eventsByWeek.set(event.gridRow, []);
        }
        eventsByWeek.get(event.gridRow).push(event);
    });

    // For each week, map global eventRow to compact display rows
    eventsByWeek.forEach((weekEvents, gridRow) => {
        // Get unique eventRows in this week, sorted chronologically
        const uniqueEventRows = [...new Set(weekEvents.map(e => e.eventRow))].sort((a, b) => a - b);

        // Create mapping: globalEventRow -> displayRow
        const eventRowToDisplayRow = new Map();
        uniqueEventRows.forEach((globalRow, displayIndex) => {
            eventRowToDisplayRow.set(globalRow, displayIndex);
        });

        // Update cell counts based on display rows
        weekEvents.forEach(event => {
            const displayRow = eventRowToDisplayRow.get(event.eventRow);
            const startCol = event.gridColumn;
            const endCol = event.gridColumn + event.span - 1;

            for (let col = startCol; col <= endCol; col++) {
                const cellIndex = gridRow * 7 + col;
                if (cellIndex < gridDates.length) {
                    cellDisplayRowCount.set(cellIndex, Math.max(cellDisplayRowCount.get(cellIndex) || 0, displayRow + 1));
                }
            }
        });
    });

    return cellDisplayRowCount;
}

/**
 * Get events organized with proper row tracking for vertical stacking
 * @param {Array} events
 * @param {Array} gridDates - Array of Date objects for each cell in the grid
 * @returns {Object} Object with multiDayEvents array and singleDayEvents map
 */
function organizeEventsForGrid(events, gridDates) {
    const singleDayEvents = new Map();
    const multiDayEventsList = [];

    // Initialize map for all grid dates
    gridDates.forEach((date) => {
        const dateKey = getDateKey(date);
        singleDayEvents.set(dateKey, []);
    });

    if (!events) return { multiDayEvents: multiDayEventsList, singleDayEvents };

    // Create a map of date to grid index
    const dateToIndex = new Map();
    gridDates.forEach((date, index) => {
        dateToIndex.set(getDateKey(date), index);
    });

    // Track which rows are occupied globally (across all weeks)
    const globalRowOccupancy = []; // Array of arrays representing occupied cells globally

    // Sort events by start date to ensure earlier events get lower row numbers
    const sortedEvents = [...events].sort((a, b) => {
        const dateA = parseEventDate(a.start);
        const dateB = parseEventDate(b.start);
        return dateA - dateB;
    });

    sortedEvents.forEach(event => {
        const startDate = parseEventDate(event.start);
        const multiDay = isMultiDayEvent(event);

        if (multiDay || event.all_day) {
            // Calculate grid positions for multi-day events
            let endDate = parseEventDate(event.end);

            // For timed events ending exactly at midnight, treat as ending on previous day
            // E.g., event ending at "2026-01-10T23:00:00+00:00" (Jan 11 00:00 local) should end on Jan 10
            if (!event.all_day && endDate.getHours() === 0 && endDate.getMinutes() === 0 && endDate.getSeconds() === 0) {
                // Subtract one day
                endDate = new Date(endDate);
                endDate.setDate(endDate.getDate() - 1);
                console.log(`  "${event.summary}" ends at midnight, adjusted end date to ${getDateKey(endDate)}`);
            }

            const startKey = getDateKey(startDate);
            const endKey = getDateKey(endDate);

            const startIndex = dateToIndex.get(startKey);
            const endIndex = dateToIndex.get(endKey);

            // Render if event starts in grid OR if it ends in grid (catches events that started before grid)
            if (startIndex !== undefined || (endIndex !== undefined && startIndex === undefined)) {
                // Determine the range of weeks this event spans
                const eventStartsBeforeGrid = startIndex === undefined;
                const eventEndsAfterGrid = endIndex === undefined;

                const firstWeekIndex = startIndex !== undefined ? Math.floor(startIndex / 7) : 0;
                const lastWeekIndex = endIndex !== undefined ? Math.floor(endIndex / 7) : Math.floor((gridDates.length - 1) / 7);

                // Collect all cells this event will occupy across all weeks
                const occupiedCells = [];
                for (let weekIdx = firstWeekIndex; weekIdx <= lastWeekIndex; weekIdx++) {
                    let colStart;
                    if (weekIdx === firstWeekIndex && startIndex !== undefined) {
                        colStart = startIndex % 7;
                    } else {
                        colStart = 0;
                    }

                    let colEnd;
                    if (weekIdx === lastWeekIndex && endIndex !== undefined) {
                        const endCol = endIndex % 7;
                        // For all-day events, endIndex is exclusive (one day past the last day)
                        // For timed events ending on a specific day, we want to include that day
                        // Since endIndex points to the end date, and end dates are exclusive for all-day events,
                        // we need to go back one day UNLESS it's a timed event ending on that specific day
                        if (event.all_day) {
                            colEnd = endCol - 1; // Exclusive end for all-day events
                        } else {
                            colEnd = endCol; // Inclusive - show on the end day for timed events
                        }
                    } else {
                        colEnd = 6; // End of week
                    }

                    // Only add cells if colEnd >= colStart (valid range)
                    if (colEnd >= colStart) {
                        for (let col = colStart; col <= colEnd; col++) {
                            const cellIndex = weekIdx * 7 + col;
                            occupiedCells.push(cellIndex);
                        }
                    }
                }

                // Find a row that can fit this event globally
                // To maintain chronological order (top to bottom), check rows sequentially from 0
                // and use the first row where this event doesn't spatially overlap
                let eventRow = 0;
                let foundRow = false;

                // Check rows from 0 upward to maintain chronological ordering
                for (let rowIdx = 0; rowIdx < globalRowOccupancy.length; rowIdx++) {
                    const row = globalRowOccupancy[rowIdx];
                    let canFit = true;

                    // Check if all cells this event needs are free in this row
                    for (const cellIndex of occupiedCells) {
                        if (row[cellIndex]) {
                            canFit = false;
                            break;
                        }
                    }

                    if (canFit) {
                        eventRow = rowIdx;
                        foundRow = true;
                        break;
                    }
                }

                // If no existing row can fit this event, create a new row
                if (!foundRow) {
                    eventRow = globalRowOccupancy.length;
                    globalRowOccupancy.push(new Array(gridDates.length).fill(false));
                }

                console.log(`✓ "${event.summary}" assigned to eventRow ${eventRow}, will appear in weeks ${firstWeekIndex}-${lastWeekIndex}`);

                // Mark all cells as occupied in this row
                for (const cellIndex of occupiedCells) {
                    globalRowOccupancy[eventRow][cellIndex] = true;
                    // Note: cellEventRowCount will be recalculated later with display rows
                }

                // Create a spanning element for each week the event appears in
                for (let weekIdx = firstWeekIndex; weekIdx <= lastWeekIndex; weekIdx++) {
                    // Calculate column start for this week
                    let colStart;
                    if (weekIdx === firstWeekIndex && startIndex !== undefined) {
                        colStart = startIndex % 7;
                    } else {
                        colStart = 0; // Start from beginning of week
                    }

                    // Calculate span for this week
                    let span;
                    if (weekIdx === lastWeekIndex && endIndex !== undefined) {
                        const endCol = endIndex % 7;
                        // For all-day events, endIndex is exclusive (one day past the last day to include)
                        // For timed events, endIndex is the actual end day (inclusive)
                        if (event.all_day) {
                            span = endCol - colStart; // Exclusive end
                        } else {
                            span = endCol - colStart + 1; // Inclusive end for timed events
                        }
                    } else {
                        // Not the last week - span to end of week
                        span = 7 - colStart;
                    }

                    // Skip if span is 0 or negative (shouldn't happen, but safety check)
                    if (span <= 0) continue;

                    // Determine if this segment should show arrow indicators
                    const showLeftArrow = (weekIdx === firstWeekIndex && eventStartsBeforeGrid) ||
                                         (weekIdx > firstWeekIndex);
                    const showRightArrow = (weekIdx === lastWeekIndex && eventEndsAfterGrid) ||
                                          (weekIdx < lastWeekIndex);

                    multiDayEventsList.push({
                        ...event,
                        gridColumn: colStart,
                        gridRow: weekIdx,
                        span: span,
                        eventRow: eventRow,
                        showLeftArrow: showLeftArrow,
                        showRightArrow: showRightArrow
                    });
                }
            }
        } else {
            // Single-day timed event
            const dateKey = getDateKey(startDate);
            if (singleDayEvents.has(dateKey)) {
                singleDayEvents.get(dateKey).push(event);
            }
        }
    });

    return { multiDayEvents: multiDayEventsList, singleDayEvents };
}

/**
 * Create a single-day timed event element (with dot)
 * @param {Object} event
 * @returns {HTMLElement}
 */
function createSingleDayTimedEvent(event) {
    const eventEl = document.createElement('div');
    eventEl.className = 'calendar-event-timed';

    const calendarClass = getCalendarClass(event.calendar_name);
    if (calendarClass) {
        eventEl.classList.add(calendarClass);
    }

    // Check if event has ended (is in the past)
    const now = new Date();
    const eventEnd = parseEventDate(event.end);
    if (eventEnd < now) {
        eventEl.classList.add('event-past');
    }

    // Dot indicator
    const dot = document.createElement('span');
    dot.className = 'event-dot';
    eventEl.appendChild(dot);

    // Event text
    const text = document.createElement('span');
    const timeStr = formatEventTime(event.start, false);
    text.textContent = `${timeStr} ${event.summary}`;
    text.className = 'event-text';
    eventEl.appendChild(text);

    eventEl.title = event.summary;
    return eventEl;
}

/**
 * Create a multi-day spanning event element with absolute positioning
 * @param {Object} event - Event with gridColumn, gridRow, span, and eventRow properties
 * @param {number} cellWidth - Width of a single day cell in percentage
 * @param {number} cellHeightPx - Height of a single week row in pixels
 * @returns {HTMLElement}
 */
function createSpanningEvent(event, cellWidth, cellHeightPx) {
    const eventEl = document.createElement('div');
    eventEl.className = 'calendar-event-spanning';

    // Calculate position - width uses percentage, top uses pixels (matches fixed 20px stripe height)
    const left = event.gridColumn * cellWidth;
    const width = event.span * cellWidth;

    // Calculate top position in pixels (matches the fixed 20px event stripe height in CSS)
    // Day number takes ~26px, each event row is 22px (20px height + 2px gap)
    const dayNumberOffsetPx = 26; // Fixed pixel offset for day number
    const eventRowHeightPx = 22; // Fixed pixel height per event row (20px stripe + 2px gap)
    const top = (event.gridRow * cellHeightPx) + dayNumberOffsetPx + (event.eventRow * eventRowHeightPx);

    // Calculate z-index: lower eventRow (earlier events) should have higher z-index
    // This works with the reverse rendering order to ensure proper visual stacking
    const zIndex = 100 - event.eventRow;

    console.log(`Rendering "${event.summary}": gridRow=${event.gridRow}, eventRow=${event.eventRow}, top=${top.toFixed(2)}px, z-index=${zIndex}`);

    eventEl.style.left = `calc(${left}% + 2px)`; // Add 2px left margin
    eventEl.style.width = `calc(${width}% - 4px)`; // Subtract 2px from each side
    eventEl.style.top = `${top}px`;
    eventEl.style.zIndex = String(zIndex);

    const calendarClass = getCalendarClass(event.calendar_name);
    if (calendarClass) {
        eventEl.classList.add(calendarClass);
    }

    // Add arrow indicators for events that continue beyond visible segment
    if (event.showLeftArrow) {
        eventEl.classList.add('has-left-arrow');
    }
    if (event.showRightArrow) {
        eventEl.classList.add('has-right-arrow');
    }

    // Check if event has ended (is in the past)
    const now = new Date();
    const eventEnd = parseEventDate(event.end);
    if (eventEnd < now) {
        eventEl.classList.add('event-past');
    }

    eventEl.textContent = event.summary;
    eventEl.title = event.summary;
    return eventEl;
}

/**
 * Render the calendar month grid
 * @param {Object} calendarData - Calendar data from WebSocket
 */
function renderCalendar(calendarData) {
    const container = document.getElementById(ElementId.CALENDAR_CONTAINER);
    const updatedEl = document.getElementById(ElementId.CALENDAR_UPDATED);

    if (!container) {
        console.error('Calendar container not found');
        return;
    }

    // Update timestamp
    if (updatedEl && calendarData && calendarData.updated) {
        updatedEl.textContent = `Updated: ${calendarData.updated}`;
    }

    // Get current date
    const today = new Date();
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth();

    // Clear existing content
    container.innerHTML = '';

    // Create calendar structure
    const calendarGrid = document.createElement('div');
    calendarGrid.className = 'calendar-month-grid';

    // Month header with legend
    const monthHeader = document.createElement('div');
    monthHeader.className = 'calendar-month-header';

    // Legend (left side) - two columns
    const legendContainer = document.createElement('div');
    legendContainer.className = 'calendar-legend';

    // Column 1: Personal calendars
    const legendCol1 = document.createElement('div');
    legendCol1.className = 'calendar-legend-column';

    const rejdyItem = document.createElement('div');
    rejdyItem.className = 'calendar-legend-item';
    rejdyItem.innerHTML = '<span class="legend-dot legend-dot-rejdy"></span><span>Rejdy</span>';
    legendCol1.appendChild(rejdyItem);

    const zuzItem = document.createElement('div');
    zuzItem.className = 'calendar-legend-item';
    zuzItem.innerHTML = '<span class="legend-dot legend-dot-zuz"></span><span>Zuzana</span>';
    legendCol1.appendChild(zuzItem);

    legendContainer.appendChild(legendCol1);

    // Column 2: Bank holidays
    const legendCol2 = document.createElement('div');
    legendCol2.className = 'calendar-legend-column';

    const czItem = document.createElement('div');
    czItem.className = 'calendar-legend-item';
    czItem.innerHTML = '<span class="legend-dot legend-dot-cz"></span><span>CZ Holidays</span>';
    legendCol2.appendChild(czItem);

    const skItem = document.createElement('div');
    skItem.className = 'calendar-legend-item';
    skItem.innerHTML = '<span class="legend-dot legend-dot-sk"></span><span>SK Holidays</span>';
    legendCol2.appendChild(skItem);

    legendContainer.appendChild(legendCol2);

    monthHeader.appendChild(legendContainer);

    // Month/Year title (right side)
    const monthTitle = document.createElement('div');
    monthTitle.className = 'calendar-month-title';
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
    monthTitle.textContent = `${monthNames[currentMonth]} ${currentYear}`;
    monthHeader.appendChild(monthTitle);

    calendarGrid.appendChild(monthHeader);

    // Weekday headers (Monday first)
    const weekdayHeader = document.createElement('div');
    weekdayHeader.className = 'calendar-weekday-header';
    const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    weekdays.forEach(day => {
        const dayEl = document.createElement('div');
        dayEl.className = 'calendar-weekday';
        dayEl.textContent = day;
        weekdayHeader.appendChild(dayEl);
    });
    calendarGrid.appendChild(weekdayHeader);

    // Build array of all dates in the grid
    const gridDates = [];
    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);
    const daysInMonth = getDaysInMonth(currentYear, currentMonth);
    const daysInPrevMonth = getDaysInMonth(currentYear, currentMonth - 1);

    // Previous month's trailing days
    for (let i = firstDay - 1; i >= 0; i--) {
        const date = new Date(currentYear, currentMonth - 1, daysInPrevMonth - i);
        gridDates.push(date);
    }

    // Current month's days
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(currentYear, currentMonth, day);
        gridDates.push(date);
    }

    // Next month's leading days
    const totalCells = gridDates.length;
    const remainingCells = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
    for (let day = 1; day <= remainingCells; day++) {
        const date = new Date(currentYear, currentMonth + 1, day);
        gridDates.push(date);
    }

    // Organize events for grid rendering
    const { multiDayEvents, singleDayEvents } = organizeEventsForGrid(
        calendarData && calendarData.events ? calendarData.events : [],
        gridDates
    );

    // Calculate display rows (compacted per-week) for proper cell spacing
    const cellDisplayRowCount = calculateDisplayRows(multiDayEvents, gridDates);

    // Calendar grid - use CSS Grid for day cells
    const daysGrid = document.createElement('div');
    daysGrid.className = 'calendar-days-grid';

    // Render day cells
    gridDates.forEach((date, index) => {
        const dayCell = document.createElement('div');
        dayCell.className = 'calendar-day-cell';

        // Check if this date is in current month
        if (date.getMonth() !== currentMonth) {
            dayCell.classList.add('calendar-day-other-month');
        }

        // Highlight today
        if (isSameDay(date, today)) {
            dayCell.classList.add('calendar-day-today');
        }

        // Day number
        const dayNumber = document.createElement('div');
        dayNumber.className = 'calendar-day-number';
        dayNumber.textContent = date.getDate();
        dayCell.appendChild(dayNumber);

        // Events container for single-day timed events only
        const eventsContainer = document.createElement('div');
        eventsContainer.className = 'calendar-day-events';

        // Store cell data for resize calculations
        dayCell.dataset.cellIndex = index;

        const dateKey = getDateKey(date);
        const dayTimedEvents = singleDayEvents.get(dateKey) || [];
        const spanningEventRows = cellDisplayRowCount.get(index) || 0;

        // We'll calculate visible events dynamically in the resize observer
        // For initial render, use a conservative estimate
        const initialMaxSpanning = 4;
        const initialMaxTimed = 3;

        // Add top margin to push timed events below spanning events
        if (spanningEventRows > 0) {
            eventsContainer.style.marginTop = `${Math.min(spanningEventRows, initialMaxSpanning) * 22}px`;
        }

        // Render single-day timed events (with dots) - initially limited
        dayTimedEvents.slice(0, initialMaxTimed).forEach(event => {
            eventsContainer.appendChild(createSingleDayTimedEvent(event));
        });

        // Combined "+X more" indicator placeholder
        // Will be populated/updated by ResizeObserver
        const moreEl = document.createElement('div');
        moreEl.className = 'calendar-event-more';
        moreEl.style.display = 'none'; // Hidden initially, shown if needed
        eventsContainer.appendChild(moreEl);

        dayCell.appendChild(eventsContainer);
        daysGrid.appendChild(dayCell);
    });

    // Create a wrapper for the days grid with relative positioning
    const daysGridWrapper = document.createElement('div');
    daysGridWrapper.className = 'calendar-days-wrapper';
    daysGridWrapper.appendChild(daysGrid);

    calendarGrid.appendChild(daysGridWrapper);
    container.appendChild(calendarGrid);

    // Wait for DOM to render, then calculate dimensions and add spanning events
    requestAnimationFrame(() => {
        // Create wrapper for multi-day events with absolute positioning
        const eventsOverlay = document.createElement('div');
        eventsOverlay.className = 'calendar-events-overlay';

        // Calculate dimensions for positioning
        const numWeeks = Math.ceil(gridDates.length / 7);
        const cellWidth = 100 / 7; // Each column is 1/7 of the width (percentage)
        const cellHeightPx = daysGrid.offsetHeight / numWeeks; // Actual pixel height per week row

        // Group events by week and map global eventRow to per-week display rows
        const eventsByWeek = new Map();
        multiDayEvents.forEach(event => {
            if (!eventsByWeek.has(event.gridRow)) {
                eventsByWeek.set(event.gridRow, []);
            }
            eventsByWeek.get(event.gridRow).push(event);
        });

        // Sort events for rendering by eventRow (reverse order for correct z-index stacking)
        // Use global eventRow directly - NO per-week compaction to maintain visual consistency
        const sortedEvents = multiDayEvents.sort((a, b) => {
            if (a.gridRow !== b.gridRow) {
                return a.gridRow - b.gridRow; // Same week together
            }
            return b.eventRow - a.eventRow; // Within week: higher eventRow renders first (so lower appears on top)
        });

        // Debug: Check for duplicates
        const pausalnyEvents = sortedEvents.filter(e => e.summary && e.summary.includes("PAUSALNY"));
        console.log(`PAUSALNY segments: ${pausalnyEvents.length} total`);
        pausalnyEvents.forEach(e => {
            console.log(`  - gridRow=${e.gridRow}, gridColumn=${e.gridColumn}, span=${e.span}, eventRow=${e.eventRow}`);
        });

        // Add multi-day spanning events to overlay
        sortedEvents.forEach(event => {
            const eventEl = createSpanningEvent(event, cellWidth, cellHeightPx);
            // Don't hide anything initially - let ResizeObserver handle it
            eventsOverlay.appendChild(eventEl);
        });

        daysGridWrapper.appendChild(eventsOverlay);

        // Add ResizeObserver to recalculate event positions and visibility on zoom/resize
        const resizeObserver = new ResizeObserver(() => {
            const newCellHeightPx = daysGrid.offsetHeight / numWeeks;

            // Calculate spacing constants
            const dayNumberHeightPx = 26;
            const moreIndicatorHeightPx = 18;
            const eventRowHeightPx = 22; // 20px height + 2px gap
            const timedEventHeightPx = 18; // Approximate height for timed events

            // Calculate available height (use all space except day number)
            const availableHeight = newCellHeightPx - dayNumberHeightPx;

            // Update all spanning event positions (but don't decide visibility yet)
            const spanningEvents = eventsOverlay.querySelectorAll('.calendar-event-spanning');
            spanningEvents.forEach((eventEl, index) => {
                const event = sortedEvents[index];
                if (event) {
                    const newTop = (event.gridRow * newCellHeightPx) + dayNumberHeightPx + (event.eventRow * eventRowHeightPx);
                    eventEl.style.top = `${newTop}px`;
                }
            });

            // Calculate visibility PER CELL based on each cell's actual content
            // First pass: calculate limits for each cell
            const cellLimits = new Map(); // Map of cellIndex -> maxVisibleSpanning

            gridDates.forEach((date, index) => {
                const dateKey = getDateKey(date);
                const dayTimedEvents = singleDayEvents.get(dateKey) || [];
                const totalSpanningInCell = cellDisplayRowCount.get(index) || 0;

                // Calculate how much space this specific cell needs
                const spaceNeededForSpanning = totalSpanningInCell * eventRowHeightPx;
                const spaceNeededForTimed = dayTimedEvents.length * timedEventHeightPx;
                const totalNeeded = spaceNeededForSpanning + spaceNeededForTimed;

                let maxVisibleSpanning;
                if (totalNeeded <= availableHeight) {
                    // Everything fits - show all
                    maxVisibleSpanning = totalSpanningInCell;
                } else {
                    // Need to hide some - calculate with indicator
                    const availableWithIndicator = availableHeight - moreIndicatorHeightPx;
                    // Try to fit as many spanning as possible, leaving room for at least some timed events
                    const reservedForTimed = dayTimedEvents.length > 0 ? timedEventHeightPx : 0;
                    maxVisibleSpanning = Math.max(1, Math.floor((availableWithIndicator - reservedForTimed) / eventRowHeightPx));
                    maxVisibleSpanning = Math.min(maxVisibleSpanning, totalSpanningInCell);
                }

                cellLimits.set(index, maxVisibleSpanning);
            });

            // Second pass: apply visibility based on per-cell limits
            spanningEvents.forEach((eventEl, idx) => {
                const event = sortedEvents[idx];
                if (event) {
                    // Find all cells this event spans across
                    const startCol = event.gridColumn;
                    const endCol = event.gridColumn + event.span - 1;
                    const row = event.gridRow;

                    // Check if this event should be visible in ANY of the cells it spans
                    let shouldBeVisible = false;
                    for (let col = startCol; col <= endCol; col++) {
                        const cellIndex = row * 7 + col;
                        const cellLimit = cellLimits.get(cellIndex) || 0;
                        if (event.eventRow < cellLimit) {
                            shouldBeVisible = true;
                            break;
                        }
                    }

                    eventEl.style.display = shouldBeVisible ? 'flex' : 'none';
                }
            });

            // Third pass: Update "+X more" indicators per cell
            gridDates.forEach((date, index) => {
                const dateKey = getDateKey(date);
                const dayTimedEvents = singleDayEvents.get(dateKey) || [];
                const totalSpanningInCell = cellDisplayRowCount.get(index) || 0;
                const maxVisibleSpanning = cellLimits.get(index) || 0;

                // Calculate remaining space after spanning events
                const usedHeight = maxVisibleSpanning * eventRowHeightPx;
                const remainingHeight = availableHeight - usedHeight - (totalSpanningInCell > maxVisibleSpanning ? moreIndicatorHeightPx : 0);
                const maxVisibleTimed = Math.max(0, Math.floor(remainingHeight / timedEventHeightPx));
                const visibleTimed = Math.min(dayTimedEvents.length, maxVisibleTimed);

                // Calculate hidden counts
                const hiddenSpanning = Math.max(0, totalSpanningInCell - maxVisibleSpanning);
                const hiddenTimed = Math.max(0, dayTimedEvents.length - visibleTimed);
                const totalHidden = hiddenSpanning + hiddenTimed;

                // Update timed events visibility and margin
                const dayCell = daysGrid.children[index];
                if (dayCell) {
                    const eventsContainer = dayCell.querySelector('.calendar-day-events');
                    if (eventsContainer) {
                        // Update margin for timed events container
                        eventsContainer.style.marginTop = `${maxVisibleSpanning * eventRowHeightPx}px`;

                        // Show/hide timed events
                        const timedEventEls = eventsContainer.querySelectorAll('.calendar-event-timed');
                        timedEventEls.forEach((el, i) => {
                            if (i >= visibleTimed) {
                                el.style.display = 'none';
                            } else {
                                el.style.display = 'flex';
                            }
                        });

                        // Update "+X more" indicator
                        const moreEl = eventsContainer.querySelector('.calendar-event-more');
                        if (moreEl) {
                            if (totalHidden > 0) {
                                moreEl.textContent = `+${totalHidden} more`;
                                moreEl.style.display = 'block';
                            } else {
                                moreEl.style.display = 'none';
                            }
                        }
                    }
                }
            });
        });

        resizeObserver.observe(daysGrid);
    });

    const eventCount = calendarData && calendarData.events ? calendarData.events.length : 0;
    console.log(`📅 Rendered month-view calendar with ${eventCount} events`);
}

// Export for use in other modules
window.renderCalendar = renderCalendar;
