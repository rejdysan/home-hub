# System Architecture

> Deep dive into the Home Hub architecture, design patterns, and component interactions.

---

## High-Level Architecture

```mermaid
flowchart LR
    subgraph Edge["Edge Layer"]
        S1["🌡️ DS18B20<br/>Temperature"]
        S2["🌡️ DS18B20<br/>Temperature"]
        S3["📊 BME280<br/>Multi-Sensor"]
    end

    subgraph Transport["Transport Layer"]
        MQTT["📡 Mosquitto<br/>MQTT Broker"]
    end

    subgraph Core["Application Core"]
        API["🔌 FastAPI<br/>Server"]
        WS["🔄 WebSocket<br/>Manager"]
        BG["⏱️ Background<br/>Tasks"]
    end

    subgraph Data["Data Layer"]
        DB[(💾 SQLite)]
        CACHE["📋 In-Memory<br/>Cache"]
    end

    subgraph Presentation["Presentation Layer"]
        WEB["📺 Dashboard"]
    end

    S1 & S2 & S3 --> MQTT
    MQTT --> API
    API <--> DB
    API --> CACHE
    BG --> CACHE
    API <--> WS
    WS <--> WEB
    CACHE --> WS

    style Edge fill:#e0f2fe,stroke:#0284c7
    style Transport fill:#fee2e2,stroke:#dc2626
    style Core fill:#dcfce7,stroke:#16a34a
    style Data fill:#fef3c7,stroke:#d97706
    style Presentation fill:#f3e8ff,stroke:#9333ea
```

---

## Design Principles

### 1. Event-Driven Architecture

The system uses an event-driven approach where data flows through the system reactively:

- **MQTT Messages**: Sensors publish data on topics, server subscribes and reacts
- **WebSocket Broadcasts**: State changes trigger immediate client updates
- **Background Tasks**: Periodic fetches that broadcast on data change

### 2. Separation of Concerns

```mermaid
graph TB
    subgraph Layers["Application Layers"]
        direction TB
        PRES["Presentation<br/>(HTML, CSS, JS)"]
        API_L["API Layer<br/>(Routes, WebSocket)"]
        SERVICE["Service Layer<br/>(MQTT Handler, System Monitor)"]
        DATA_L["Data Layer<br/>(Database, Models)"]
        CONFIG["Configuration<br/>(Environment, Constants)"]
    end

    PRES --> API_L
    API_L --> SERVICE
    SERVICE --> DATA_L
    DATA_L --> CONFIG
    SERVICE --> CONFIG

    style Layers fill:#f0fdf4
```

### 3. Typed Data Models

All data flowing through the system uses strongly-typed dataclasses:

```mermaid
classDiagram
    class SensorReading {
        +str sensor
        +str prop
        +float temp
        +str ts
        +to_dict() Dict
    }

    class CurrentWeather {
        +str updated
        +int temp
        +int feels
        +bool is_day
        +int code
        +str desc
        +Dict forecast
        +equals_ignoring_updated() bool
    }

    class BusDeparture {
        +str line
        +str direction
        +int mins
        +str time_predicted
        +int delay_minutes
    }

    class SystemStats {
        +float cpu
        +float ram_pct
        +float disk_pct
        +Optional~float~ cpu_temp
        +empty() SystemStats
    }

    class NamedayResponse {
        +str country
        +str nameday
        +from_dict() NamedayResponse
    }
```

---

## Message Flow Patterns

### Pattern 1: Sensor Data Ingestion

```mermaid
sequenceDiagram
    participant Sensor as IoT Sensor
    participant MQTT as MQTT Broker
    participant Handler as MQTT Handler
    participant DB as Database
    participant WS as WebSocket Manager
    participant Client as Dashboard

    Sensor->>MQTT: PUBLISH pico/temperature/bedroom
    MQTT->>Handler: on_message callback
    
    Note over Handler: Update sensor_last_seen
    Note over Handler: Check throttle window
    
    alt Throttle passed (>5s)
        Handler->>DB: save_reading()
        Handler->>Handler: Trigger callback
        Handler->>WS: broadcast_sensor_update()
        WS->>Client: {"type": "sensors", "data": [...]}
    else Within throttle window
        Note over Handler: Skip DB save<br/>Still update last_seen
    end
```

### Pattern 2: Client Connection

```mermaid
sequenceDiagram
    participant Client as Dashboard
    participant WS as WebSocket Endpoint
    participant Manager as WS Manager
    participant DB as Database
    participant Cache as Memory Cache

    Client->>WS: WebSocket CONNECT /ws
    WS->>Manager: connect(websocket)
    Manager->>Manager: Add to active_connections
    
    WS->>DB: get_current_status()
    WS->>Cache: Get weather, transport, system
    
    WS->>Client: InitialStateMessage
    Note over Client: Full state snapshot

    loop Keep-alive
        Client-->>WS: (silence for 30s)
        WS->>Client: HeartbeatMessage
    end

    Client->>WS: WebSocket DISCONNECT
    WS->>Manager: disconnect(websocket)
```

### Pattern 3: External API Polling

```mermaid
sequenceDiagram
    participant Task as Background Task
    participant API as External API
    participant Cache as Memory Cache
    participant WS as WebSocket Manager
    participant Client as Dashboard

    loop Every N seconds
        Task->>API: HTTP GET request
        API->>Task: JSON response
        
        Task->>Task: Parse into typed model
        
        alt Data changed
            Task->>Cache: Update cached value
            Task->>WS: broadcast(update_message)
            WS->>Client: Push update
        else No change
            Note over Task: Skip broadcast
        end
    end
```

---

## Component Interactions

### Application Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Starting: python main.py
    
    Starting --> InitDB: Initialize database
    InitDB --> InitMQTT: Connect MQTT
    InitMQTT --> StartTasks: Launch background tasks
    StartTasks --> Running: Server ready
    
    Running --> Running: Handle requests
    
    Running --> Stopping: SIGTERM/SIGINT
    Stopping --> CancelTasks: Cancel background tasks
    CancelTasks --> StopMQTT: Disconnect MQTT
    StopMQTT --> [*]: Shutdown complete
```

### Background Task Coordination

```mermaid
flowchart TB
    subgraph Lifespan["FastAPI Lifespan Context"]
        INIT["Initialization"]
        YIELD["yield (app running)"]
        CLEANUP["Cleanup"]
    end

    subgraph Tasks["Concurrent Tasks"]
        T1["🖥️ System Monitor<br/>Every 2s"]
        T2["🌤️ Weather Update<br/>Every 10min"]
        T3["📅 Nameday Update<br/>Every 6h"]
        T4["🚌 Bus Update<br/>Every 30s"]
        T5["🔍 Sensor Status<br/>Every 5s"]
    end

    INIT --> |"asyncio.create_task()"| T1 & T2 & T3 & T4 & T5
    T1 & T2 & T3 & T4 & T5 --> |"running"| YIELD
    YIELD --> |"task.cancel()"| CLEANUP

    style Tasks fill:#dcfce7
```

---

## Thread Safety

The application handles threading carefully due to MQTT callbacks running in a separate thread:

```mermaid
flowchart TB
    subgraph MainThread["Main Thread (asyncio)"]
        LOOP["Event Loop"]
        WS["WebSocket Handlers"]
        HTTP["HTTP Handlers"]
        TASKS["Background Tasks"]
    end

    subgraph MQTTThread["MQTT Thread"]
        CALLBACK["on_message callback"]
    end

    CALLBACK -->|"asyncio.run_coroutine_threadsafe()"| LOOP
    LOOP --> WS & HTTP & TASKS

    style MainThread fill:#dcfce7
    style MQTTThread fill:#fee2e2
```

The `_main_loop` reference is captured at startup and used for thread-safe coroutine scheduling:

```python
# Captured in lifespan
_main_loop = asyncio.get_running_loop()

# Used in MQTT callback (different thread)
asyncio.run_coroutine_threadsafe(
    broadcast_sensor_update(name, prop, val),
    _main_loop
)
```

---

## Error Handling Strategy

```mermaid
flowchart TB
    subgraph Startup["Startup Errors"]
        DB_FAIL["Database init failed"]
        MQTT_FAIL["MQTT connect failed"]
        DB_FAIL & MQTT_FAIL --> ABORT["Abort startup"]
    end

    subgraph Runtime["Runtime Errors"]
        API_TIMEOUT["External API timeout"]
        WS_ERROR["WebSocket send failed"]
        SENSOR_ERROR["Sensor data invalid"]
        
        API_TIMEOUT --> LOG_WARN["Log warning<br/>Continue loop"]
        WS_ERROR --> DISCONNECT["Remove connection<br/>Continue"]
        SENSOR_ERROR --> SKIP["Skip processing<br/>Log debug"]
    end

    subgraph Recovery["Automatic Recovery"]
        MQTT_RECONNECT["MQTT auto-reconnect"]
        WS_RECONNECT["Client auto-reconnect"]
    end

    style Startup fill:#fee2e2
    style Runtime fill:#fef3c7
    style Recovery fill:#dcfce7
```

---

## Scalability Considerations

### Current Design (Single Node)

The current architecture is optimized for single Raspberry Pi deployment:

- SQLite for simplicity and low resource usage
- In-memory caching for frequently accessed data
- Single WebSocket manager instance

### Potential Scaling Points

| Component | Current | Scalable Alternative |
|-----------|---------|---------------------|
| Database | SQLite | PostgreSQL, TimescaleDB |
| Message Queue | In-memory | Redis Pub/Sub |
| WebSocket | Single instance | Redis-backed adapter |
| Caching | Dict/variables | Redis |

```mermaid
flowchart TB
    subgraph Future["Scaled Architecture (Future)"]
        LB["Load Balancer"]
        
        subgraph Nodes["Application Nodes"]
            N1["Node 1"]
            N2["Node 2"]
        end
        
        REDIS["Redis<br/>Pub/Sub + Cache"]
        TSDB["TimescaleDB"]
        
        LB --> N1 & N2
        N1 & N2 <--> REDIS
        N1 & N2 --> TSDB
    end

    style Future fill:#f0fdf4
```

