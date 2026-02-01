import RPi.GPIO as GPIO
import time
import json
import paho.mqtt.client as mqtt
from datetime import datetime
import subprocess
import os
import base64

# ==========================
# GPIO
# ==========================
PROX_PIN = 23

# ==========================
# MQTT
# ==========================
BROKER_ADDRESS = "raspberrypi.local"
PROX_TOPIC = "senior_connect/sensors/proximity"
CAMERA_TOPIC = "senior_connect/sensors/camera"

# ==========================
# SENSOR INFO
# ==========================
SENSOR_TYPE = "Proximity"
LOCATION = "Living Room Main Door"

IMAGE_PATH = "/home/pi/entrance.jpg"

# ==========================
# GPIO SETUP
# ==========================
GPIO.setmode(GPIO.BCM)
GPIO.setup(PROX_PIN, GPIO.IN)

client = mqtt.Client()

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def connect_mqtt():
    client.connect(BROKER_ADDRESS, 1883, 60)
    client.loop_start()
    print("🟢 Connected to Central Controller")

def publish_proximity(value, status):
    payload = {
        "type": SENSOR_TYPE,
        "location": LOCATION,
        "value": value,
        "status": status,
        "time": timestamp()
    }
    client.publish(PROX_TOPIC, json.dumps(payload))
    print(f"📤 Proximity Sent → {payload}")

def take_and_send_photo():
    print("📸 Camera Triggered")
    subprocess.call(f"raspistill -o {IMAGE_PATH} -w 640 -h 480 -t 1", shell=True)

    if os.path.exists(IMAGE_PATH):
        with open(IMAGE_PATH, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode()

        payload = {
            "type": "Camera",
            "location": LOCATION,
            "image": encoded_image,
            "time": timestamp()
        }

        client.publish(CAMERA_TOPIC, json.dumps(payload))
        print("📤 Image Sent to Controller")

# ==========================
# MAIN LOOP
# ==========================
print("🚪 Proximity + Camera Sensor Running...")
print("Press CTRL+C to stop.")

connect_mqtt()
last_state = None   # EXACTLY like proxBathroom.py

try:
    while True:
        prox_value = GPIO.input(PROX_PIN)

        # ---- DETECTED ----
        if prox_value == 1:
            if last_state != "Detected":
                print(f"[{timestamp()}] 🚶 Detected")
                publish_proximity("Detected", "Active")
                take_and_send_photo()
                last_state = "Detected"

        # ---- CLEAR ----
        else:
            if last_state != "Clear":
                print(f"[{timestamp()}] 🚪 Clear")
                publish_proximity("Clear", "Inactive")
                last_state = "Clear"

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n🛑 Stopping...")

finally:
    GPIO.cleanup()
    client.loop_stop()
    client.disconnect()
