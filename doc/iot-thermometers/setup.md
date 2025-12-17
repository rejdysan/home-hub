# Raspberry PI Pico 2WH - MQTT publisher for DS18B20 temperature sensor

## Hardware
- Raspberry Pi Pico 2WH
- DS18B20 temperature sensor (see [picture](ds18b20-waterproof.webp))
  - one-wire digital temperature sensor
  - requires one data line (and GND) to communicate with Raspberry Pi Pico
  - each DS18B20 temperature sensor has a unique 64-bit serial code
  - power supply range: 3.0V to 5.5V
  - operating temperature range: -55ºC to +125ºC
  - accuracy +/-0.5 ºC (between the range -10ºC to 85ºC)
- 4.7k Ohm resistor
- Breadboard and jumper wires

## Wiring the DS18B20 to the Raspberry Pi Pico
- See [schematic diagram](raspberry-pi-pico-ds18b20-wiring_bb.webp)

## Software
- MicroPython firmware for Raspberry Pi Pico 2WH
- Thonny IDE

## MicroPython using MQTT
- MQTT stands for Message Queuing Telemetry Transport. MQTT is a simple messaging protocol designed for constrained devices with low bandwidth.
- For further details see [official website](https://mqtt.org/).

# Installing MQTT MicroPython Modules
- see [umqtt.simply.py](./raspberry-pi-pico-2w-micropython/umqtt/simple.md)
- see [umqtt.robust.py](./raspberry-pi-pico-2w-micropython/umqtt/robust.md)

# Create a configuration file
- see [config.py](./raspberry-pi-pico-2w-micropython/config.md)
- `mqtt_server` - if using a local Mosquitto MQTT broker, you should pass the broker IP address without the port

# Publishing MQTT Messages
- with following code we will publish MQTT messages on a certain topic with our Raspberry Pi Pico.
- we will use following code [main.py](./raspberry-pi-pico-2w-micropython/main.md)
- the code contains:
  - imports of necessary modules
  - setting up static IP for our Raspberry Pi Pico (not needed)
  - setting MQTT parameters. For example topic name `pico/temperature/bedroom`, plus others.
  - setting up the DS18B20 sensor
  - function to read temperature from the DS18B20 sensor
  - function to connect to Wi-Fi with static IP (not needed)
  - connect MQTT client to the broker
  - main loop to read temperature and publish it to the MQTT broker every 10 seconds
  - code also handles reconnection to Wi-Fi and MQTT broker if the connection is lost
  
- all the mentioned files need to be uploaded to the Raspberry Pi Pico using Thonny IDE in the same folder structure as in the [folder](./raspberry-pi-pico-2w-micropython)

## Sources
- [Raspberry Pi Pico: DS18B20 Temperature Sensor (MicroPython) – Single and Multiple](https://randomnerdtutorials.com/raspberry-pi-pico-ds18b20-micropython/)
- [Raspberry Pi Pico W: Getting Started with MQTT (MicroPython)](https://randomnerdtutorials.com/raspberry-pi-pico-w-mqtt-micropython/)