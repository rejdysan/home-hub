# IoT Sensors - Raspberry Pi Pico 2W Setup

> Hardware setup and MicroPython code for temperature and environmental sensors publishing data via MQTT.

---

## System Overview

```mermaid
flowchart LR
    subgraph Sensors["IoT Sensors"]
        direction TB
        PICO1["Pico 2W + DS18B20<br/>Temperature Only"]
        PICO2["Pico 2W + BME280<br/>Multi-Sensor"]
    end

    subgraph Network["Local Network"]
        WIFI["WiFi Router"]
    end

    subgraph Hub["Raspberry Pi 5"]
        MQTT["Mosquitto MQTT Broker"]
        APP["Home Hub Server"]
    end

    PICO1 -->|"WiFi"| WIFI
    PICO2 -->|"WiFi"| WIFI
    WIFI --> MQTT
    MQTT --> APP

    style Sensors fill:#e0f2fe,stroke:#0284c7
    style Hub fill:#dcfce7,stroke:#16a34a
```

---

## Sensor Comparison

| Feature | DS18B20 | BME280 |
|---------|---------|--------|
| **Interface** | 1-Wire | I2C |
| **Measurements** | Temperature | Temperature, Humidity, Pressure |
| **Accuracy** | ±0.5°C | ±1°C, ±3% RH, ±1 hPa |
| **Range** | -55°C to +125°C | -40°C to +85°C |
| **Power** | 3.0V - 5.5V | 1.8V - 3.6V |
| **Use Case** | Indoor rooms | Outdoor/environmental |

---

# DS18B20 Temperature Sensor Setup

## Hardware Components

- Raspberry Pi Pico 2WH
- DS18B20 temperature sensor (see [picture](ds18b20.webp))
  - One-wire digital temperature sensor
  - Unique 64-bit serial code per sensor
  - Power supply: 3.0V to 5.5V
  - Operating range: -55°C to +125°C
  - Accuracy: ±0.5°C (between -10°C to 85°C)
- 4.7kΩ pull-up resistor
- Breadboard and jumper wires

## Wiring Diagram

```mermaid
flowchart LR
    subgraph Pico["Raspberry Pi Pico 2W"]
        GPIO22["GPIO 22"]
        GND["GND"]
        V3["3.3V"]
    end

    subgraph Sensor["DS18B20"]
        DATA["Data (Yellow)"]
        SGND["GND (Black)"]
        VCC["VCC (Red)"]
    end

    RESISTOR["4.7kΩ Resistor"]

    GPIO22 --- DATA
    GND --- SGND
    V3 --- VCC
    V3 --- RESISTOR
    RESISTOR --- DATA

    style Pico fill:#dcfce7
    style Sensor fill:#fef3c7
```

See [schematic diagram](raspberry-pi-pico-ds18b20-wiring_bb.webp) for detailed wiring.

## Software Requirements

- MicroPython firmware for Raspberry Pi Pico 2WH
- Thonny IDE for uploading code
- MQTT library (umqtt)

## MQTT Topic Structure

```
pico/temperature/{sensor_name}
```

Example: `pico/temperature/bedroom`

## Code Files Required

| File | Purpose |
|------|---------|
| [config.py](./raspberry-pi-pico-2w-micropython/config.md) | WiFi and MQTT credentials |
| [main.py](./raspberry-pi-pico-2w-micropython/main-temperature-ds18b20.md) | Main sensor loop |
| [umqtt/simple.py](./raspberry-pi-pico-2w-micropython/umqtt/simple.md) | MQTT client library |
| [umqtt/robust.py](./raspberry-pi-pico-2w-micropython/umqtt/robust.md) | Robust MQTT wrapper |

## Data Flow

```mermaid
sequenceDiagram
    participant Sensor as DS18B20
    participant Pico as Pico 2W
    participant MQTT as MQTT Broker
    participant Hub as Home Hub

    loop Every 10 seconds
        Pico->>Sensor: Request temperature
        Sensor->>Pico: Return temperature value
        
        alt Valid reading
            Pico->>MQTT: PUBLISH pico/temperature/bedroom
            MQTT->>Hub: Forward message
        else Invalid (85°C or out of range)
            Pico->>Pico: Skip, retry next cycle
        end
    end
```

---

# BME280 Multi-Sensor Setup

## Hardware Components

- Raspberry Pi Pico 2WH
- BME280 sensor module (see [picture](bme280.webp))
  - I2C digital environmental sensor
  - I2C address: 0x76 (default) or 0x77
  - Power supply: 1.8V to 3.6V
  - Temperature range: -40°C to +85°C
  - Humidity range: 0% to 100% RH
  - Pressure range: 300 to 1100 hPa
- Breadboard and jumper wires

## Wiring Diagram

```mermaid
flowchart LR
    subgraph Pico["Raspberry Pi Pico 2W"]
        GPIO5["GPIO 5 (SCL)"]
        GPIO4["GPIO 4 (SDA)"]
        GND["GND"]
        V3["3.3V"]
    end

    subgraph Sensor["BME280 Module"]
        SCL["SCL"]
        SDA["SDA"]
        SGND["GND"]
        VCC["VCC"]
    end

    GPIO5 --- SCL
    GPIO4 --- SDA
    GND --- SGND
    V3 --- VCC

    style Pico fill:#dcfce7
    style Sensor fill:#fef3c7
```

See [schematic diagram](raspberry-Pi-Pico-BME280-circuit-diagram_bb.webp) for detailed wiring.

## MQTT Topic Structure

The BME280 publishes to three separate topics:

```
pico/temperature/{sensor_name}
pico/humidity/{sensor_name}
pico/pressure/{sensor_name}
```

Example topics for balcony sensor:
- `pico/temperature/balcony`
- `pico/humidity/balcony`
- `pico/pressure/balcony`

## Code Files Required

| File | Purpose |
|------|---------|
| [config.py](./raspberry-pi-pico-2w-micropython/config.md) | WiFi and MQTT credentials |
| [main.py](./raspberry-pi-pico-2w-micropython/main-multisensor-bme280.md) | Main sensor loop |
| [BME280.py](./raspberry-pi-pico-2w-micropython/BME280.md) | BME280 I2C driver |
| [umqtt/simple.py](./raspberry-pi-pico-2w-micropython/umqtt/simple.md) | MQTT client library |
| [umqtt/robust.py](./raspberry-pi-pico-2w-micropython/umqtt/robust.md) | Robust MQTT wrapper |

## Data Flow

```mermaid
sequenceDiagram
    participant Sensor as BME280
    participant Pico as Pico 2W
    participant MQTT as MQTT Broker
    participant Hub as Home Hub

    loop Every 10 seconds
        Pico->>Sensor: Read via I2C
        Sensor->>Pico: Temperature, Humidity, Pressure
        
        Pico->>MQTT: PUBLISH pico/temperature/balcony
        Pico->>MQTT: PUBLISH pico/humidity/balcony
        Pico->>MQTT: PUBLISH pico/pressure/balcony
        
        MQTT->>Hub: Forward messages
    end
```

---

## LED Status Patterns

Both sensors use the onboard LED for visual feedback:

```mermaid
flowchart TB
    subgraph Patterns["LED Status Patterns"]
        SLOW["Slow Blink (0.5s)"]
        QUICK2["2 Quick Blinks"]
        MEDIUM3["3 Medium Blinks"]
        FAST4["4 Fast Blinks"]
        VFAST2["2 Very Fast Blinks"]
        PULSE["Brief Off-Pulse"]
    end

    SLOW --> |"Meaning"| WIFI_CONN["WiFi Connecting"]
    QUICK2 --> |"Meaning"| SUCCESS["Connection Success"]
    MEDIUM3 --> |"Meaning"| WIFI_ERR["WiFi Error"]
    FAST4 --> |"Meaning"| MQTT_ERR["MQTT Error"]
    VFAST2 --> |"Meaning"| SENSOR_ERR["Sensor Error"]
    PULSE --> |"Meaning"| HEARTBEAT["Data Sent Successfully"]

    style Patterns fill:#e0f2fe
```

| Pattern | Duration | Meaning |
|---------|----------|---------|
| Slow blink | 0.5s on/off | WiFi connecting |
| 2 quick blinks | 0.1s each | Connection successful |
| 3 medium blinks | 0.2s each | WiFi error |
| 4 fast blinks | 0.15s each | MQTT error |
| 2 very fast blinks | 0.1s each | Sensor read error |
| Brief off-pulse | 50ms | Data transmitted |

---

## Watchdog Timer

Both sensor implementations include a watchdog timer for automatic recovery:

```mermaid
flowchart LR
    START["Device Running"]
    FEED["wdt.feed()"]
    TIMEOUT["8 Second Timeout"]
    RESET["Automatic Reset"]

    START --> |"Every loop iteration"| FEED
    FEED --> |"Resets timer"| START
    START --> |"If code hangs"| TIMEOUT
    TIMEOUT --> RESET
    RESET --> START

    style TIMEOUT fill:#fee2e2
    style RESET fill:#fef3c7
```

The watchdog timer (`WDT`) ensures the device automatically restarts if:
- Code enters an infinite loop
- Network operation hangs
- Sensor communication fails

---

## File Structure on Pico

Upload files to the Pico using Thonny IDE:

```
/
├── main.py          # Main sensor code
├── config.py        # WiFi/MQTT credentials
├── BME280.py        # (BME280 only) I2C driver
└── umqtt/
    ├── simple.py    # MQTT client
    └── robust.py    # Robust wrapper
```

---

## Configuration Template

Edit `config.py` with your network settings:

```python
wifi_ssid = 'YourWiFiName'
wifi_password = 'YourWiFiPassword'
mqtt_server = b'192.168.0.50'  # Raspberry Pi 5 IP
mqtt_username = b'pico_bedroom'
mqtt_password = b'your_mqtt_password'
```

---

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| No LED activity | No power | Check USB connection |
| Slow blinking forever | WiFi not connecting | Verify SSID/password |
| 4 fast blinks | MQTT connection failed | Check broker IP and credentials |
| Reading 85°C | DS18B20 power issue | Check wiring and pull-up resistor |
| No sensor found | I2C address wrong | Try 0x77 instead of 0x76 |

---

## References

- [Raspberry Pi Pico: DS18B20 Temperature Sensor (MicroPython)](https://randomnerdtutorials.com/raspberry-pi-pico-ds18b20-micropython/)
- [Raspberry Pi Pico W: Getting Started with MQTT (MicroPython)](https://randomnerdtutorials.com/raspberry-pi-pico-w-mqtt-micropython/)
- [Raspberry Pi Pico: BME280 Get Temperature, Humidity, and Pressure (MicroPython)](https://randomnerdtutorials.com/raspberry-pi-pico-bme280-micropython/)
