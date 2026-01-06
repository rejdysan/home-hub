/**
 * Updates module
 * Handles UI updates for sensors, weather, system info, etc.
 */

// Global sensor status from backend (real-time tracking)
window.sensorStatus = {};

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
        document.getElementById(ElementId.HOME_BEDROOM).textContent = val ? val.toFixed(1) : '--';
    }

    // Living Room
    const livKey = groups[SensorName.LIVING_ROOM] ? SensorName.LIVING_ROOM : SensorName.LIVING_ROOM_LOWER;
    if (groups[livKey]) {
        const val = groups[livKey].props[SensorProperty.TEMPERATURE] || groups[livKey].props[SensorProperty.TEMP];
        document.getElementById(ElementId.HOME_LIVING).textContent = val ? val.toFixed(1) : '--';
    }

    // Balcony
    const balcKey = groups[SensorName.BALCONY] ? SensorName.BALCONY : SensorName.BALCONY_LOWER;
    if (groups[balcKey]) {
        const props = groups[balcKey].props;
        const t = props[SensorProperty.TEMPERATURE] || props[SensorProperty.TEMP];
        const h = props[SensorProperty.HUMIDITY] || props[SensorProperty.HUMID];
        const p = props[SensorProperty.PRESSURE] || props[SensorProperty.PRESS];

        document.getElementById(ElementId.HOME_BALCONY_TEMP).textContent = t ? t.toFixed(1) : '--';
        document.getElementById(ElementId.HOME_BALCONY_HUM).textContent = h ? Math.round(h) : '--';
        document.getElementById(ElementId.HOME_BALCONY_PRESS).textContent = p ? Math.round(p) : '--';
    }

    // Update status indicators based on backend-provided status
    updateSensorStatusIndicators();
}

/**
 * Update weather display
 * @param {Object} w - Weather data object
 */
function updateWeather(w) {
    // Fix: Corrected logic error - check if temp is undefined
    if (w?.temp === undefined) return;

    document.getElementById(ElementId.TODAY_TEMP).textContent = w.temp + '°';
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

        w.forecast.time.forEach((d, i) => {
            const date = new Date(d);
            const dayName = i === 0 ? "Today" : date.toLocaleDateString(Locale.DATE, DateFormat.SHORT_WEEKDAY);

            const dayBox = document.createElement('div');
            dayBox.className = CssClass.FC_DAY_BOX;

            const dateDiv = document.createElement('div');
            dateDiv.className = CssClass.FC_DATE;
            dateDiv.textContent = dayName;

            const icon = document.createElement('i');
            icon.setAttribute('data-lucide', window.getWeatherIconName(w.forecast.weather_code[i]));
            icon.style.cssText = 'width:30px;height:30px;margin:20px 0';

            const tempMax = document.createElement('div');
            tempMax.className = CssClass.FC_TEMP;
            tempMax.textContent = Math.round(w.forecast.temperature_2m_max[i]) + '°';

            const tempMin = document.createElement('div');
            tempMin.style.cssText = 'font-size:1rem; opacity:0.6';
            tempMin.textContent = Math.round(w.forecast.temperature_2m_min[i]) + '°';

            dayBox.appendChild(dateDiv);
            dayBox.appendChild(icon);
            dayBox.appendChild(tempMax);
            dayBox.appendChild(tempMin);

            forecastRow.appendChild(dayBox);
        });
    }

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
    document.getElementById(ElementId.CPU_PCT).textContent = sys.cpu + '%';
    document.getElementById(ElementId.CPU_TEMP).textContent = (sys.cpu_temp || DefaultConfig.DEFAULT_CPU_TEMP) + '°C';
    document.getElementById(ElementId.RAM_PCT).textContent = sys.ram_pct + '%';
    document.getElementById(ElementId.RAM_DETAIL).textContent = `${sys.ram_used} / ${sys.ram_total} GB`;
    document.getElementById(ElementId.DISK_PCT).textContent = sys.disk_pct + '%';
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
