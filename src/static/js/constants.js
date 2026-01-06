/**
 * Constants and Enums module
 * Centralized definitions for magic strings, colors, and configuration
 */

// ============================================================================
// WebSocket Message Types
// ============================================================================
const MessageType = Object.freeze({
    INITIAL: 'initial',
    SENSORS: 'sensors',
    SENSOR_STATUS: 'sensor_status',
    WEATHER: 'weather',
    NAMEDAY: 'nameday',
    SYSTEM: 'system',
    TRANSPORT: 'transport',
    HEARTBEAT: 'heartbeat',
    TODOIST: 'todoist',
    CALENDAR: 'calendar'
});

// ============================================================================
// Kiosk Display Modes
// ============================================================================
const KioskMode = Object.freeze({
    MORNING: 'morning',
    DAY: 'day',
    NIGHT: 'night'
});

// ============================================================================
// Sensor Names and Properties
// ============================================================================
const SensorName = Object.freeze({
    BEDROOM: 'Bedroom',
    BEDROOM_LOWER: 'bedroom',
    LIVING_ROOM: 'Living Room',
    LIVING_ROOM_LOWER: 'livingroom',
    BALCONY: 'Balcony',
    BALCONY_LOWER: 'balcony'
});

const SensorProperty = Object.freeze({
    TEMPERATURE: 'temperature',
    TEMP: 'temp',
    HUMIDITY: 'humidity',
    HUMID: 'humid',
    PRESSURE: 'pressure',
    PRESS: 'press'
});

// ============================================================================
// DOM Element IDs
// ============================================================================
const ElementId = Object.freeze({
    // Clock
    CLOCK_TIME: 'clock-time',
    CLOCK_DATE: 'clock-date',

    // Maps & Calendars
    MAP_FRAME_1: 'map-frame-1',
    MAP_FRAME_2: 'map-frame-2',
    CALENDAR_FRAME_1: 'calendar-frame-1',
    CALENDAR_FRAME_2: 'calendar-frame-2',
    UPDATE_MAP_1: 'update-map1',
    UPDATE_MAP_2: 'update-map2',
    UPDATE_CAL_1: 'update-cal1',
    UPDATE_CAL_2: 'update-cal2',

    // Weather
    WEATHER_RECT: 'weather-rect',
    TODAY_TEMP: 'today-temp',
    WEATHER_FEELS: 'w-feels',
    WEATHER_DESC: 'w-desc',
    WEATHER_WIND: 'w-wind',
    WEATHER_HUM: 'w-hum',
    WEATHER_PRES: 'w-pres',
    WEATHER_VIS: 'w-vis',
    WEATHER_UV: 'w-uv',
    WEATHER_CLOUD: 'w-cloud',
    WEATHER_UPDATED: 'w-updated',
    FORECAST_ROW: 'forecast-row',
    MAIN_ICON: 'main-icon',

    // Sensors
    STATUS_BEDROOM: 'status-bedroom',
    STATUS_LIVING: 'status-living',
    STATUS_BALCONY: 'status-balcony',
    HOME_BEDROOM: 'home-bedroom',
    HOME_LIVING: 'home-living',
    HOME_BALCONY_TEMP: 'home-balcony-temp',
    HOME_BALCONY_HUM: 'home-balcony-hum',
    HOME_BALCONY_PRESS: 'home-balcony-press',

    // System
    CPU_PCT: 'cpu-pct',
    CPU_TEMP: 'cpu-temp',
    RAM_PCT: 'ram-pct',
    RAM_DETAIL: 'ram-detail',
    DISK_PCT: 'disk-pct',
    DISK_DETAIL: 'disk-detail',
    NET_DOWN: 'net-down',
    NET_UP: 'net-up',
    NET_DETAIL: 'net-detail',

    // Health
    HEALTH_MQTT: 'health-mqtt',
    HEALTH_DB: 'health-db',
    HEALTH_WIFI: 'health-wifi',

    // Nameday
    NAMEDAY_INFO: 'nameday-info',

    // Transport
    BUS_LIST_MALESICKA: 'bus-list-malesicka',
    BUS_LIST_OLGY: 'bus-list-olgy',

    // Calendar
    CALENDAR_CONTAINER: 'calendar-container',
    CALENDAR_UPDATED: 'calendar-updated'
});

// ============================================================================
// CSS Classes
// ============================================================================
const CssClass = Object.freeze({
    // Status indicators
    STATUS_DOT: 'status-dot',
    STATUS_ONLINE: 'status-online',
    STATUS_OFFLINE: 'status-offline',

    // Layout
    RECT: 'rect',
    TOP_CONTAINER: 'top-container',
    BOTTOM_CONTAINER: 'bottom-container',
    BOTTOM_LEFT: 'bottom-left',

    // Kiosk modes
    NIGHT_MODE: 'night-mode',
    NIGHT_MODE_CLOCK: 'night-mode-clock',

    // Weather backgrounds
    BG_CLEAR_DAY: 'bg-clear-day',
    BG_CLEAR_NIGHT: 'bg-clear-night',
    BG_CLOUDY: 'bg-cloudy',
    BG_RAINY: 'bg-rainy',
    BG_SNOWY: 'bg-snowy',
    BG_STORM: 'bg-storm',

    // Bus
    BUS_ITEM: 'bus-item',
    BUS_LINE: 'bus-line',
    BUS_DIRECTION: 'bus-direction',
    BUS_TIMES: 'bus-times',
    BUS_TIME_PREDICTED: 'bus-time-predicted',
    BUS_TIME_SCHEDULED: 'bus-time-scheduled',
    BUS_MINS: 'bus-mins',
    BUS_MINS_VALUE: 'bus-mins-value',
    BUS_MINS_UNIT: 'bus-mins-unit',
    BUS_URGENT: 'bus-urgent',
    BUS_NO_DATA: 'bus-no-data',

    // Forecast
    FC_DAY_BOX: 'fc-day-box',
    FC_DATE: 'fc-date',
    FC_TEMP: 'fc-temp',

    // Calendar
    CALENDAR_EVENT: 'calendar-event',
    CALENDAR_EVENT_REJDY: 'calendar-event-rejdy',
    CALENDAR_EVENT_ZUZ: 'calendar-event-zuz',
    CALENDAR_EVENT_CZ: 'calendar-event-cz',
    CALENDAR_EVENT_SK: 'calendar-event-sk',
    CALENDAR_EVENT_TIME: 'calendar-event-time',
    CALENDAR_EVENT_TITLE: 'calendar-event-title',
    CALENDAR_NO_EVENTS: 'calendar-no-events'
});

// ============================================================================
// Weather Icons (Lucide)
// ============================================================================
const WeatherIcon = Object.freeze({
    SUN: 'sun',
    CLOUD_SUN: 'cloud-sun',
    CLOUD: 'cloud',
    CLOUD_RAIN: 'cloud-rain',
    CLOUD_SNOW: 'cloud-snow',
    CLOUD_LIGHTNING: 'cloud-lightning'
});

// ============================================================================
// Colors
// ============================================================================
const Color = Object.freeze({
    // Bus line colors
    BUS_LINE_133: '#3b82f6',
    BUS_LINE_146: '#ec4899',
    BUS_LINE_155: '#10b981',
    BUS_LINE_DEFAULT: '#64748b',

    // Status colors
    DELAY_LATE: '#f87171',
    DELAY_EARLY: '#4ade80',
    DELAY_DEFAULT: '#e2e8f0',

    // Time colors
    TIME_SOON: '#4ade80',
    TIME_LATER: '#fbbf24'
});

// Bus line color mapping
const BusLineColors = Object.freeze({
    '133': Color.BUS_LINE_133,
    '146': Color.BUS_LINE_146,
    '155': Color.BUS_LINE_155
});

// ============================================================================
// Locales
// ============================================================================
const Locale = Object.freeze({
    TIME: 'en-GB',
    DATE: 'en-US'
});

// ============================================================================
// Date Format Options
// ============================================================================
const DateFormat = Object.freeze({
    FULL_DATE: { weekday: 'long', day: 'numeric', month: 'long' },
    SHORT_WEEKDAY: { weekday: 'short' }
});

// ============================================================================
// Time Intervals (milliseconds)
// ============================================================================
const Interval = Object.freeze({
    CLOCK_UPDATE: 1000,
    KIOSK_CHECK: 1000,
    WEBSOCKET_RECONNECT: 2000,
    DEFAULT_MAP_REFRESH: 60000,
    DEFAULT_CALENDAR_REFRESH: 3000000000
});

// ============================================================================
// Default Configuration Values
// ============================================================================
const DefaultConfig = Object.freeze({
    MORNING_MODE_START: '00:00',
    DAY_MODE_START: '00:01',
    NIGHT_MODE_START: '23:59',
    DEFAULT_CPU_TEMP: 'N/A',
    API_PORT: 8000,
    BUS_SLOTS: 5,
    EARLY_THRESHOLD: -10
});

// ============================================================================
// API Endpoints
// ============================================================================
const ApiEndpoint = Object.freeze({
    CONFIG: '/api/config',
    WEBSOCKET: '/ws'
});

// ============================================================================
// Sensor to Element ID Mapping
// ============================================================================
const SensorElementMap = Object.freeze({
    [SensorName.BEDROOM]: ElementId.STATUS_BEDROOM,
    [SensorName.BEDROOM_LOWER]: ElementId.STATUS_BEDROOM,
    [SensorName.LIVING_ROOM]: ElementId.STATUS_LIVING,
    [SensorName.LIVING_ROOM_LOWER]: ElementId.STATUS_LIVING,
    [SensorName.BALCONY]: ElementId.STATUS_BALCONY,
    [SensorName.BALCONY_LOWER]: ElementId.STATUS_BALCONY
});

// ============================================================================
// CSS Selectors
// ============================================================================
const Selector = Object.freeze({
    TOP_CONTAINER: '.top-container',
    BOTTOM_CONTAINER: '.bottom-container',
    MAP_RECTS: '.top-container .rect:nth-child(1), .top-container .rect:nth-child(2)',
    CLOCK_RECT: '.bottom-container .rect.bottom-left',
    OTHER_BOTTOM_RECTS: '.bottom-container .rect:not(.bottom-left)',
    HEALTH_MQTT_DOT: '#health-mqtt .status-dot',
    HEALTH_DB_DOT: '#health-db .status-dot',
    HEALTH_WIFI_DOT: '#health-wifi .status-dot'
});

// ============================================================================
// Export to window for use in other modules
// ============================================================================
window.MessageType = MessageType;
window.KioskMode = KioskMode;
window.SensorName = SensorName;
window.SensorProperty = SensorProperty;
window.ElementId = ElementId;
window.CssClass = CssClass;
window.WeatherIcon = WeatherIcon;
window.Color = Color;
window.BusLineColors = BusLineColors;
window.Locale = Locale;
window.DateFormat = DateFormat;
window.Interval = Interval;
window.DefaultConfig = DefaultConfig;
window.ApiEndpoint = ApiEndpoint;
window.SensorElementMap = SensorElementMap;
window.Selector = Selector;

