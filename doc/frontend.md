# Frontend Documentation

> Dashboard UI, WebSocket communication, kiosk modes, and client-side architecture.

---

## Dashboard Layout

```mermaid
flowchart TB
    subgraph Layout["Dashboard Grid Layout"]
        subgraph Top["Top Container (4 columns)"]
            MAP1["🗺️ Traffic Map 1<br/>Direct Route"]
            MAP2["🗺️ Traffic Map 2<br/>Via Waypoint"]
            CAL1["📅 Calendar 1"]
            CAL2["📅 Calendar 2"]
        end
        
        subgraph Bottom["Bottom Container (3 columns)"]
            LEFT["⏰ Clock & System<br/>Health Status"]
            CENTER["🌤️ Weather Panel<br/>Home Sensors"]
            RIGHT["🚌 Transport<br/>Bus Departures"]
        end
    end

    style Top fill:#e0f2fe
    style Bottom fill:#dcfce7
```

---

## Module Architecture

The frontend is organized into focused JavaScript modules:

```mermaid
flowchart TB
    subgraph Modules["JavaScript Modules"]
        CONSTANTS["constants.js<br/>Enums & Config"]
        CLOCK["clock.js<br/>Time Display"]
        IFRAME["iframe.js<br/>Map/Calendar Refresh"]
        WEATHER["weather.js<br/>Weather Icons & BG"]
        TRANSPORT["transport.js<br/>Bus List Rendering"]
        UPDATES["updates.js<br/>UI Update Functions"]
        WEBSOCKET["websocket.js<br/>Server Connection"]
        KIOSK["kiosk.js<br/>Display Modes"]
    end

    APP["app.js<br/>Entry Point"]
    
    APP --> CONSTANTS
    APP --> CLOCK & IFRAME & KIOSK
    APP --> WEBSOCKET
    WEBSOCKET --> UPDATES
    UPDATES --> WEATHER & TRANSPORT

    style APP fill:#fef3c7
    style Modules fill:#dcfce7
```

### Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `constants.js` | Enums, element IDs, CSS classes, config values |
| `clock.js` | Real-time clock display, date formatting |
| `iframe.js` | Google Maps and Calendar iframe refresh |
| `weather.js` | Weather icon mapping, dynamic backgrounds |
| `transport.js` | Bus departure list rendering |
| `updates.js` | DOM updates for all data types |
| `websocket.js` | WebSocket connection, message routing |
| `kiosk.js` | Time-based display mode switching |
| `app.js` | Application initialization, config fetch |

---

## WebSocket Communication

### Connection Flow

```mermaid
sequenceDiagram
    participant App as app.js
    participant WS as websocket.js
    participant Server as Backend
    participant Updates as updates.js

    App->>WS: connect()
    WS->>Server: WebSocket /ws
    Server->>WS: InitialStateMessage
    WS->>Updates: updateSensors()
    WS->>Updates: updateWeather()
    WS->>Updates: updateTransport()
    WS->>Updates: updateSystem()
    
    loop Real-time Updates
        Server->>WS: TypedMessage
        WS->>Updates: Appropriate update function
        Updates->>Updates: Update DOM
    end
    
    alt Connection Lost
        WS->>WS: setTimeout(connect, 3000)
    end
```

### Message Type Handling

```javascript
// Message type routing
switch (msg.type) {
    case 'initial':     // Full state on connect
    case 'sensors':     // Sensor readings
    case 'sensor_status': // Online/offline
    case 'weather':     // Weather data
    case 'nameday':     // Nameday string
    case 'system':      // Host metrics
    case 'transport':   // Bus departures
    case 'heartbeat':   // Keep-alive
}
```

---

## Kiosk Display Modes

The dashboard automatically adjusts based on time of day:

```mermaid
flowchart TB
    subgraph Cycle["Daily Display Cycle"]
        direction LR
        NIGHT["Night Mode"]
        MORNING["Morning Mode"]
        DAY["Day Mode"]
        
        NIGHT -->|"05:30"| MORNING
        MORNING -->|"08:00"| DAY
        DAY -->|"22:00"| NIGHT
    end

    subgraph NightDetails["Night 22:00-05:30"]
        N1["Clock Only"]
        N2["Black Background"]
        N3["Minimal Power"]
    end

    subgraph MorningDetails["Morning 05:30-08:00"]
        M1["Full Dashboard"]
        M2["Maps + Calendars"]
        M3["Weather + Transport"]
    end

    subgraph DayDetails["Day 08:00-22:00"]
        D1["Calendars Expanded"]
        D2["Maps Hidden"]
        D3["Weather + Transport"]
    end

    NIGHT -.-> NightDetails
    MORNING -.-> MorningDetails
    DAY -.-> DayDetails

    style NIGHT fill:#1e293b,color:#fff
    style MORNING fill:#fef3c7,stroke:#d97706
    style DAY fill:#e0f2fe,stroke:#0284c7
```

### Mode Configuration

| Mode | Time Range | Visible Elements |
|------|------------|------------------|
| **Morning** | 05:30 - 08:00 | Everything |
| **Day** | 08:00 - 22:00 | Calendars, Weather, Transport, Clock |
| **Night** | 22:00 - 05:30 | Clock only |

### CSS Classes Applied

```mermaid
flowchart LR
    subgraph Night["Night Mode"]
        BODY["body.night-mode"]
        CLOCK["clock.night-mode-clock"]
    end

    BODY --> |"Sets"| BG["Black background"]
    CLOCK --> |"Enlarges"| SIZE["Full-screen clock"]

    style Night fill:#1e293b,color:#fff
```

---

## Weather Display

### Weather Icons

Weather codes are mapped to Lucide icons:

| Code Range | Condition | Icon |
|------------|-----------|------|
| 0 | Clear sky | `sun` |
| 1-3 | Partly cloudy | `cloud-sun` |
| 45-48 | Fog | `cloud` |
| 51-67 | Rain/Drizzle | `cloud-rain` |
| 71-77 | Snow | `cloud-snow` |
| 80-82 | Rain showers | `cloud-rain` |
| 85-86 | Snow showers | `cloud-snow` |
| 95-99 | Thunderstorm | `cloud-lightning` |

### Dynamic Backgrounds

The weather panel changes background based on conditions:

```mermaid
flowchart LR
    CODE["Weather Code"]
    
    CODE --> |"0-1 + day"| CLEAR_DAY["☀️ Clear Day<br/>Blue gradient"]
    CODE --> |"0-1 + night"| CLEAR_NIGHT["🌙 Clear Night<br/>Dark blue"]
    CODE --> |"2-48"| CLOUDY["☁️ Cloudy<br/>Gray gradient"]
    CODE --> |"51-82"| RAINY["🌧️ Rainy<br/>Blue-gray"]
    CODE --> |"71-86"| SNOWY["❄️ Snowy<br/>White-blue"]
    CODE --> |"95+"| STORM["⛈️ Storm<br/>Dark purple"]
```

---

## Sensor Display

### Sensor Status Indicators

Each sensor has a colored status dot:

```mermaid
flowchart LR
    STATUS["Sensor Status"]
    
    STATUS --> |"online: true"| GREEN["🟢 Green dot<br/>status-online"]
    STATUS --> |"online: false"| RED["🔴 Red dot<br/>status-offline"]

    style GREEN fill:#22c55e
    style RED fill:#ef4444
```

### Sensor to Element Mapping

| Sensor Name | Display Location | Data Shown |
|-------------|------------------|------------|
| `bedroom` | Bedroom card | Temperature |
| `livingroom` | Living Room card | Temperature |
| `balcony` | Balcony card | Temperature, Humidity, Pressure |

---

## Transport Display

Bus departures are rendered with:
- Line number (badge style)
- Direction/headsign
- Scheduled time
- Predicted time (with delay indicator)
- Minutes until departure

```mermaid
flowchart TB
    subgraph BusItem["Bus Departure Item"]
        LINE["🔵 Line 146"]
        DIR["Direction: Sídliště Malešice"]
        TIMES["Scheduled: 14:30 | Predicted: 14:32"]
        MINS["⏱️ 5 min"]
    end

    style BusItem fill:#e0f2fe
```

### Urgency Styling

Departures within 2 minutes get urgent styling (red background).

---

## System Information Display

```mermaid
flowchart TB
    subgraph SystemPanel["System Monitor Panel"]
        subgraph Health["Health Status"]
            MQTT["MQTT 🟢"]
            DB["Database 🟢"]
        end
        
        subgraph Resources["Resource Usage"]
            CPU["CPU: 15%<br/>45°C"]
            RAM["RAM: 2.1GB / 8GB<br/>26%"]
            DISK["Disk: 12GB / 64GB<br/>19%"]
        end
    end

    style Health fill:#dcfce7
    style Resources fill:#e0f2fe
```

---

## External Embeds

### Google Maps

Traffic maps are embedded using Google Maps Embed API:

```
https://www.google.com/maps/embed/v1/directions
  ?key={API_KEY}
  &origin={ORIGIN}
  &destination={DESTINATION}
  &waypoints={OPTIONAL_WAYPOINT}
  &mode=driving
```

### Google Calendar

Calendars are embedded using Google Calendar embed:

```
https://calendar.google.com/calendar/embed
  ?src={CALENDAR_ID}
  &ctz=Europe/Prague
  &bgcolor=%23161b2c
  &showTitle=0
```

### Refresh Strategy

Both Maps and Calendars are refreshed by:
1. Storing original `src` URL
2. Appending timestamp parameter
3. Reassigning to iframe `src`

```javascript
iframe.src = originalSrc + "&_t=" + Date.now();
```

---

## Initialization Sequence

```mermaid
sequenceDiagram
    participant DOM as DOM Ready
    participant App as app.js
    participant API as /api/config
    participant WS as WebSocket

    DOM->>App: Load complete
    App->>App: Start clock interval
    App->>App: Start kiosk check interval
    App->>API: Fetch configuration
    API->>App: Config (intervals, kiosk times)
    App->>App: Apply kiosk mode
    App->>App: Set map/calendar refresh intervals
    App->>WS: connect()
    WS->>App: Ready for updates
```

---

## Styling Architecture

### CSS Organization

| Section | Purpose |
|---------|---------|
| Base | Reset, typography, colors |
| Layout | Grid containers, responsiveness |
| Components | Cards, badges, status dots |
| Weather | Backgrounds, forecasts |
| Transport | Bus list styling |
| Kiosk | Night mode overrides |

### Color Palette

```mermaid
flowchart LR
    subgraph Colors["Color Scheme"]
        BG["Background<br/>#161b2c"]
        CARD["Card<br/>#1e293b"]
        TEXT["Text<br/>#e2e8f0"]
        ACCENT["Accent<br/>#3b82f6"]
        SUCCESS["Success<br/>#22c55e"]
        WARNING["Warning<br/>#f59e0b"]
        ERROR["Error<br/>#ef4444"]
    end

    style BG fill:#161b2c,color:#fff
    style CARD fill:#1e293b,color:#fff
    style ACCENT fill:#3b82f6,color:#fff
    style SUCCESS fill:#22c55e,color:#fff
    style ERROR fill:#ef4444,color:#fff
```
