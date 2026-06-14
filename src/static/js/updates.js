/**
 * Updates module
 * Handles UI updates for sensors, weather, system info, etc.
 */

// Global sensor status from backend (real-time tracking)
window.sensorStatus = {};

/**
 * Set an element's text and play a "pop" animation when the value actually changed.
 * @param {string} id - Element ID
 * @param {string} text - New text content
 * @param {boolean} animate - Whether to play the change animation
 */
function setLiveValue(id, text, animate = true) {
    const el = document.getElementById(id);
    if (!el || el.textContent === text) return;
    el.textContent = text;
    if (!animate) return;
    el.classList.remove('value-pop');
    void el.offsetWidth; // force reflow so the animation can restart
    el.classList.add('value-pop');
}

/**
 * Update sensor status indicator dots based on backend status
 */
function updateSensorStatusIndicators() {
    // Create a case-insensitive lookup map from backend sensor status
    const statusLookup = {};
    for (const [name, status] of Object.entries(window.sensorStatus || {})) {
        // Normalize: remove spaces and convert to lowercase for matching
        const normalizedName = name.replace(/\s+/g, '').toLowerCase();
        statusLookup[normalizedName] = status;
    }

    // Update each status indicator
    for (const [sensorName, elementId] of Object.entries(SensorElementMap)) {
        const statusEl = document.getElementById(elementId);
        if (statusEl) {
            // Normalize the sensor name for lookup
            const normalizedName = sensorName.replace(/\s+/g, '').toLowerCase();
            const sensorStatus = statusLookup[normalizedName];

            if (sensorStatus) {
                const isOnline = sensorStatus.online;
                statusEl.className = isOnline
                    ? `${CssClass.STATUS_DOT} ${CssClass.STATUS_ONLINE}`
                    : `${CssClass.STATUS_DOT} ${CssClass.STATUS_OFFLINE}`;
            }
        }
    }
}

/**
 * Update sensor readings display
 * @param {Array} sensors - Array of sensor data objects
 */
function updateSensors(sensors) {
    if (!sensors || sensors.length === 0) return;

    // Group sensors by name, keeping all properties
    const groups = {};
    for (const s of sensors) {
        if (!groups[s.sensor]) groups[s.sensor] = {props: {}};
        groups[s.sensor].props[s.prop] = s.temp;
    }

    // Bedroom
    const bedKey = groups[SensorName.BEDROOM] ? SensorName.BEDROOM : SensorName.BEDROOM_LOWER;
    if (groups[bedKey]) {
        const val = groups[bedKey].props[SensorProperty.TEMPERATURE] || groups[bedKey].props[SensorProperty.TEMP];
        setLiveValue(ElementId.HOME_BEDROOM, val ? val.toFixed(1) : '--');
    }

    // Living Room
    const livKey = groups[SensorName.LIVING_ROOM] ? SensorName.LIVING_ROOM : SensorName.LIVING_ROOM_LOWER;
    if (groups[livKey]) {
        const val = groups[livKey].props[SensorProperty.TEMPERATURE] || groups[livKey].props[SensorProperty.TEMP];
        setLiveValue(ElementId.HOME_LIVING, val ? val.toFixed(1) : '--');
    }

    // Balcony
    const balcKey = groups[SensorName.BALCONY] ? SensorName.BALCONY : SensorName.BALCONY_LOWER;
    if (groups[balcKey]) {
        const props = groups[balcKey].props;
        const t = props[SensorProperty.TEMPERATURE] || props[SensorProperty.TEMP];
        const h = props[SensorProperty.HUMIDITY] || props[SensorProperty.HUMID];
        const p = props[SensorProperty.PRESSURE] || props[SensorProperty.PRESS];

        setLiveValue(ElementId.HOME_BALCONY_TEMP, t ? t.toFixed(1) : '--');
        setLiveValue(ElementId.HOME_BALCONY_HUM, h ? String(Math.round(h)) : '--');
        setLiveValue(ElementId.HOME_BALCONY_PRESS, p ? String(Math.round(p)) : '--');
    }

    // Update status indicators based on backend-provided status
    updateSensorStatusIndicators();
}

// Latest hourly series, kept so the "now" marker can move between weather updates
let _lastHourly = null;

/**
 * Render the 24h temperature graph (2h past → 22h ahead) as inline SVG.
 * Two lines — actual temperature and feels-like — plus a vertical "now"
 * marker with a pulsing dot on the temperature curve.
 *
 * @param {Object} hourly - {time: [...], temperature_2m: [...], apparent_temperature: [...]}
 * @param {boolean} animate - Play the line draw-in animation (true on new data,
 *                            false for the minute-by-minute "now" marker refresh)
 */
function renderTempGraph(hourly, animate = true) {
    const host = document.getElementById('w-graph');
    if (!host) return;

    const times = hourly?.time || [];
    const temps = hourly?.temperature_2m || [];
    const feels = hourly?.apparent_temperature || [];
    if (times.length < 2 || temps.length !== times.length || feels.length !== times.length) {
        host.style.display = 'none'; // backend without hourly data yet — hide gracefully
        return;
    }
    host.style.display = '';
    _lastHourly = hourly;

    const W = host.clientWidth || 560;
    // The legend occupies its own 14px row above the plot (no overlap possible)
    const H = Math.max((host.clientHeight || 124) - 14, 60);
    // Generous top/bottom padding so the high label clears the top edge and the
    // low label sits below the curve without colliding with the hour axis.
    const padL = 8, padR = 8, padT = 22, padB = 28;

    const all = temps.concat(feels);
    const vMin = Math.min(...all);
    const vMax = Math.max(...all);
    const vSpan = Math.max(vMax - vMin, 1);

    const x = i => padL + (i / (times.length - 1)) * (W - padL - padR);
    const y = v => padT + (1 - (v - vMin) / vSpan) * (H - padT - padB);

    // Smooth cubic path through the hourly points
    const smoothPath = vals => {
        let d = `M ${x(0).toFixed(1)} ${y(vals[0]).toFixed(1)}`;
        for (let i = 1; i < vals.length; i++) {
            const x0 = x(i - 1), y0 = y(vals[i - 1]);
            const x1 = x(i), y1 = y(vals[i]);
            const dx = (x1 - x0) / 2.2;
            d += ` C ${(x0 + dx).toFixed(1)} ${y0.toFixed(1)}, ${(x1 - dx).toFixed(1)} ${y1.toFixed(1)}, ${x1.toFixed(1)} ${y1.toFixed(1)}`;
        }
        return d;
    };

    const tempPath = smoothPath(temps);
    const feelsPath = smoothPath(feels);
    const areaPath = `${tempPath} L ${x(times.length - 1).toFixed(1)} ${H - padB} L ${x(0).toFixed(1)} ${H - padB} Z`;

    // "Now" position, interpolated between the surrounding hourly points
    const nowMs = Date.now();
    let idx = 0;
    for (let i = 0; i < times.length; i++) {
        if (new Date(times[i]).getTime() <= nowMs) idx = i;
    }
    const t0 = new Date(times[idx]).getTime();
    const t1 = idx < times.length - 1 ? new Date(times[idx + 1]).getTime() : t0 + 3600000;
    const frac = Math.min(Math.max((nowMs - t0) / (t1 - t0), 0), 1);
    const nowX = x(idx + frac);
    const tNow = temps[idx] + (temps[Math.min(idx + 1, temps.length - 1)] - temps[idx]) * frac;
    const nowY = y(tNow);

    // Hour labels every 4 hours along the very bottom
    let labels = '';
    for (let i = 0; i < times.length; i += 4) {
        const hh = String(new Date(times[i]).getHours()).padStart(2, '0');
        labels += `<text class="wg-time" x="${x(i).toFixed(1)}" y="${H - 4}" text-anchor="middle">${hh}</text>`;
    }

    // Mark the day's high and low on the temperature curve.
    // High label sits in the top padding; low label tucks just below its point
    // (clamped so it never drops into the hour-axis row).
    const iMax = temps.indexOf(Math.max(...temps));
    const iMin = temps.indexOf(Math.min(...temps));
    const maxLabelY = Math.max(y(temps[iMax]) - 7, 9);
    const minLabelY = Math.min(y(temps[iMin]) + 14, H - 15);
    const peakLabels =
        `<text class="wg-peak" x="${x(iMax).toFixed(1)}" y="${maxLabelY.toFixed(1)}" text-anchor="middle">${Math.round(temps[iMax])}°</text>` +
        `<text class="wg-peak" x="${x(iMin).toFixed(1)}" y="${minLabelY.toFixed(1)}" text-anchor="middle">${Math.round(temps[iMin])}°</text>`;

    host.innerHTML = `
        <div class="wg-legend">
            <span class="wg-leg-temp">Temp</span>
            <span class="wg-leg-feels">Feels</span>
        </div>
        <svg viewBox="0 0 ${W} ${H}" width="100%" class="wg${animate ? ' wg-anim' : ''}" aria-hidden="true">
            <defs>
                <linearGradient id="wg-area-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop class="wg-grad-top" offset="0%"/>
                    <stop class="wg-grad-bottom" offset="100%"/>
                </linearGradient>
            </defs>
            <path class="wg-area" d="${areaPath}" fill="url(#wg-area-grad)"/>
            <path class="wg-feels" d="${feelsPath}" pathLength="1"/>
            <path class="wg-temp" d="${tempPath}" pathLength="1"/>
            <line class="wg-now-line" x1="${nowX.toFixed(1)}" y1="${padT - 8}" x2="${nowX.toFixed(1)}" y2="${H - padB}"/>
            <circle class="wg-now-ping" cx="${nowX.toFixed(1)}" cy="${nowY.toFixed(1)}" r="4"/>
            <circle class="wg-now-dot" cx="${nowX.toFixed(1)}" cy="${nowY.toFixed(1)}" r="3"/>
            ${labels}
            ${peakLabels}
        </svg>`;
}

// Keep the "now" marker moving between weather broadcasts
setInterval(() => {
    if (_lastHourly) renderTempGraph(_lastHourly, false);
}, 60000);

/**
 * Update weather display
 * @param {Object} w - Weather data object
 */
function updateWeather(w) {
    // Fix: Corrected logic error - check if temp is undefined
    if (w?.temp === undefined) return;

    setLiveValue(ElementId.TODAY_TEMP, w.temp + '°');
    document.getElementById(ElementId.WEATHER_FEELS).textContent = w.feels;
    document.getElementById(ElementId.WEATHER_DESC).textContent = w.desc;
    document.getElementById(ElementId.WEATHER_WIND).textContent = w.wind;
    document.getElementById(ElementId.WEATHER_HUM).textContent = w.hum;
    document.getElementById(ElementId.WEATHER_PRES).textContent = w.pres;
    document.getElementById(ElementId.WEATHER_VIS).textContent = w.vis;
    document.getElementById(ElementId.WEATHER_UV).textContent = w.uv;
    document.getElementById(ElementId.WEATHER_CLOUD).textContent = w.cloud;
    document.getElementById(ElementId.WEATHER_UPDATED).textContent = "Updated: " + w.updated;

    // Forecast - Security: Use DOM manipulation instead of innerHTML to prevent XSS
    if (w.forecast?.time) {
        const forecastRow = document.getElementById(ElementId.FORECAST_ROW);
        forecastRow.innerHTML = ''; // Clear existing content

        // Week-wide range, used to position each day's min–max span bar
        const weekMin = Math.min(...w.forecast.temperature_2m_min);
        const weekMax = Math.max(...w.forecast.temperature_2m_max);
        const weekSpan = Math.max(weekMax - weekMin, 1);

        w.forecast.time.forEach((d, i) => {
            const date = new Date(d);
            const dayName = i === 0 ? "Today" : date.toLocaleDateString(Locale.DATE, DateFormat.SHORT_WEEKDAY);
            const lo = w.forecast.temperature_2m_min[i];
            const hi = w.forecast.temperature_2m_max[i];

            const col = document.createElement('div');
            col.className = i === 0 ? 'fc-col fc-col-today' : 'fc-col';
            col.style.setProperty('--i', i); // staggered entrance animation

            const dateDiv = document.createElement('div');
            dateDiv.className = CssClass.FC_DATE;
            dateDiv.textContent = dayName;

            const icon = document.createElement('i');
            icon.setAttribute('data-lucide', window.getWeatherIconName(w.forecast.weather_code[i]));
            icon.style.cssText = 'width:26px;height:26px;margin:7px 0 4px 0';

            const tempMax = document.createElement('div');
            tempMax.className = CssClass.FC_TEMP;
            tempMax.textContent = Math.round(hi) + '°';

            // Range bar: this day's span placed within the week's range
            const range = document.createElement('div');
            range.className = 'fc-range';
            const fill = document.createElement('div');
            fill.className = 'fc-range-fill';
            fill.style.left = ((lo - weekMin) / weekSpan * 100) + '%';
            fill.style.width = Math.max((hi - lo) / weekSpan * 100, 8) + '%';
            range.appendChild(fill);

            const tempMin = document.createElement('div');
            tempMin.className = 'fc-temp-min';
            tempMin.textContent = Math.round(lo) + '°';

            col.appendChild(dateDiv);
            col.appendChild(icon);
            col.appendChild(tempMax);
            col.appendChild(range);
            col.appendChild(tempMin);

            forecastRow.appendChild(col);
        });
    }

    renderTempGraph(w.hourly);

    const iconName = window.getWeatherIconName(w.code);
    document.getElementById(ElementId.MAIN_ICON).dataset.lucide = iconName;
    window.updateWeatherBackground(w.code, w.is_day);
    lucide.createIcons();
}

/**
 * Update nameday display
 * @param {string} nameday - Nameday string
 */
function updateNameday(nameday) {
    if (!nameday) return;
    document.getElementById(ElementId.NAMEDAY_INFO).textContent = "Nameday of: " + nameday;
}

/**
 * Update health status indicators
 * @param {Object} health - Health status object
 */
function updateHealth(health) {
    if (!health) return;
    const mqttDot = document.querySelector(Selector.HEALTH_MQTT_DOT);
    const dbDot = document.querySelector(Selector.HEALTH_DB_DOT);
    const wifiDot = document.querySelector(Selector.HEALTH_WIFI_DOT);

    mqttDot.className = health.mqtt
        ? `${CssClass.STATUS_DOT} ${CssClass.STATUS_ONLINE}`
        : `${CssClass.STATUS_DOT} ${CssClass.STATUS_OFFLINE}`;
    dbDot.className = health.database
        ? `${CssClass.STATUS_DOT} ${CssClass.STATUS_ONLINE}`
        : `${CssClass.STATUS_DOT} ${CssClass.STATUS_OFFLINE}`;
    wifiDot.className = health.wifi
        ? `${CssClass.STATUS_DOT} ${CssClass.STATUS_ONLINE}`
        : `${CssClass.STATUS_DOT} ${CssClass.STATUS_OFFLINE}`;
}

/**
 * Update system information display
 * @param {Object} sys - System info object
 */
function updateSystem(sys) {
    if (!sys) return;

    // Drive the conic-gradient gauge rings (CSS animates --p transitions)
    const setGauge = (id, pct) => {
        const g = document.getElementById(id);
        if (g) g.style.setProperty('--p', pct || 0);
    };
    setGauge('gauge-cpu', sys.cpu);
    setGauge('gauge-ram', sys.ram_pct);
    setGauge('gauge-disk', sys.disk_pct);

    // Whole numbers only — decimals don't fit inside the gauge rings
    document.getElementById(ElementId.CPU_PCT).textContent = Math.round(sys.cpu) + '%';
    document.getElementById(ElementId.CPU_TEMP).textContent =
        (typeof sys.cpu_temp === 'number' ? Math.round(sys.cpu_temp) : DefaultConfig.DEFAULT_CPU_TEMP) + '°C';
    document.getElementById(ElementId.RAM_PCT).textContent = Math.round(sys.ram_pct) + '%';
    document.getElementById(ElementId.RAM_DETAIL).textContent = `${sys.ram_used} / ${sys.ram_total} GB`;
    document.getElementById(ElementId.DISK_PCT).textContent = Math.round(sys.disk_pct) + '%';
    document.getElementById(ElementId.DISK_DETAIL).textContent = `${sys.disk_used} / ${sys.disk_total} GB`;

    // Network speeds - auto-convert to KB/s or MB/s with dynamic font sizing
    const downSpeed = sys.net_recv;
    const upSpeed = sys.net_sent;
    const useMB = downSpeed > 1024 || upSpeed > 1024;

    let downValue, upValue;
    if (useMB) {
        // Use decimals for MB/s
        downValue = (downSpeed / 1024).toFixed(1);
        upValue = (upSpeed / 1024).toFixed(1);
        document.getElementById(ElementId.NET_DOWN).textContent = downValue;
        document.getElementById(ElementId.NET_UP).textContent = upValue;
        document.getElementById(ElementId.NET_DETAIL).textContent = 'MB/s';
    } else {
        // No decimals for KB/s - round to integer
        downValue = Math.round(downSpeed).toString();
        upValue = Math.round(upSpeed).toString();
        document.getElementById(ElementId.NET_DOWN).textContent = downValue;
        document.getElementById(ElementId.NET_UP).textContent = upValue;
        document.getElementById(ElementId.NET_DETAIL).textContent = 'KB/s';
    }

    // Apply size classes to both number elements based on max length
    const downElement = document.getElementById(ElementId.NET_DOWN);
    const upElement = document.getElementById(ElementId.NET_UP);

    if (downElement && upElement) {
        const maxLength = Math.max(downValue.length, upValue.length);

        // Remove all size classes from both elements
        downElement.classList.remove('size-large', 'size-xlarge', 'size-xxlarge');
        upElement.classList.remove('size-large', 'size-xlarge', 'size-xxlarge');

        // Apply same size class to both for consistency
        if (maxLength >= 5) {
            downElement.classList.add('size-xxlarge');
            upElement.classList.add('size-xxlarge');
        } else if (maxLength >= 4) {
            downElement.classList.add('size-xlarge');
            upElement.classList.add('size-xlarge');
        } else if (maxLength >= 3) {
            downElement.classList.add('size-large');
            upElement.classList.add('size-large');
        }
    }
}

/**
 * Update transport/bus information
 * @param {Object} transport - Transport data object
 */
function updateTransport(transport) {
    if (!transport) return;
    window.renderBusList(transport.malesicka, ElementId.BUS_LIST_MALESICKA);
    window.renderBusList(transport.olgy, ElementId.BUS_LIST_OLGY);
}

// Export for use in other modules
window.updateSensorStatusIndicators = updateSensorStatusIndicators;
window.updateSensors = updateSensors;
window.updateWeather = updateWeather;
window.updateNameday = updateNameday;
window.updateHealth = updateHealth;
window.updateSystem = updateSystem;
window.updateTransport = updateTransport;
