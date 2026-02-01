import RPi.GPIO as GPIO
import time
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# ----- GPIO -----
PROX_PIN = 23

# ----- MQTT -----
BROKER_ADDRESS = "raspberrypi.local"   # MUST match controller broker
TOPIC = "senior_connect/sensors/proximity"

# ----- SENSOR INFO (MUST MATCH CONTROLLER) -----
SENSOR_TYPE = "Proximity"
LOCATION = "Bathroom Door"

# ----- GPIO SETUP -----
GPIO.setmode(GPIO.BCM)
GPIO.setup(PROX_PIN, GPIO.IN)

# ----- MQTT CLIENT (v2 API) -----
client = mqtt.Client()

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def connect_mqtt():
    try:
        client.connect(BROKER_ADDRESS, 1883, 60)
        client.loop_start()
        print("🟢 Connected to Central Controller")
        return True
    except Exception as e:
        print(f"🔴 MQTT Error: {e}")
        return False

def publish(value, status):
    payload = {
        "type": SENSOR_TYPE,
        "location": LOCATION,
        "value": value,
        "status": status
    }
    client.publish(TOPIC, json.dumps(payload))
    print(f"📤 Sent → {payload}")

# ----- MAIN -----
print("🚪 Bathroom Door Proximity Sensor Running...")
print("Press CTRL+C to stop.")

connected = connect_mqtt()
last_state = None   # Track state to prevent spam

try:
    while True:
        prox_value = GPIO.input(PROX_PIN)

        if prox_value == 1:
            # Door Triggered
            if last_state != "Detected":
                print(f"[{timestamp()}] 🚪 Door Triggered")
                if connected:
                    publish("Detected", "Active")
                last_state = "Detected"

        else:
            # Door Clear
            if last_state != "Clear":
                print(f"[{timestamp()}] 🚪 Door Clear")
                if connected:
                    publish("Clear", "Inactive")
                last_state = "Clear"

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n🛑 Stopping program...")

finally:
    GPIO.cleanup()
    try:
        client.loop_stop()
        client.disconnect()
    except:
        pass

