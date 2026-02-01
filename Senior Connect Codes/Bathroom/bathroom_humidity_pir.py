import json
import time
from datetime import datetime
from gpiozero import MotionSensor
import board
import adafruit_dht
import paho.mqtt.client as mqtt

# ============================
# 🎨 CONSOLE COLORS (New)
# ============================
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"

# ============================
# MQTT / Controller settings
# ============================
CONTROLLER_IP = "raspberrypi.local"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
MQTT_TOPIC = "senior_connect/sensors/data"

# ============================
# Location
# ============================
LOCATION = "Bathroom"

# ============================
# PIR settings
# ============================
PIR_PIN = 17
PIR_QUEUE_LEN = 5
PIR_SAMPLE_RATE = 10
PIR_THRESHOLD = 0.30

# ============================
# No motion interval
# ============================
NO_MOTION_INTERVAL = 5  # seconds

# ============================
# Humidity Sensor settings
# ============================
dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)
HUMIDITY_READ_INTERVAL = 5.0

# ============================
# Helper
# ============================
def ts():
    return datetime.now().strftime("%H:%M:%S") # Shortened for cleaner look

# ============================
# MQTT client
# ============================
client = mqtt.Client()

def connect_to_controller():
    print(f"{YELLOW}⏳ Connecting to {CONTROLLER_IP}...{RESET}")
    try:
        client.connect(CONTROLLER_IP, MQTT_PORT, MQTT_KEEPALIVE)
        client.loop_start()
        print(f"{GREEN}✅ CONNECTED to Controller!{RESET}")
        return True
    except Exception as e:
        print(f"{RED}❌ Connection Failed: {e}{RESET}")
        return False

def publish(payload):
    try:
        client.publish(MQTT_TOPIC, json.dumps(payload))
        # No print here to keep main loop clean, logic handled in main
    except Exception as e:
        print(f"{RED}❌ Publish failed: {e}{RESET}")

# ============================
# Main
# ============================
def main():
    print(f"\n{BOLD}🛁 SENIOR CONNECT: {LOCATION} Node{RESET}")
    print("--------------------------------")
    
    pir = MotionSensor(
        PIR_PIN,
        queue_len=PIR_QUEUE_LEN,
        sample_rate=PIR_SAMPLE_RATE,
        threshold=PIR_THRESHOLD
    )

    print(f"{YELLOW}⚡ Warming up PIR sensor (30s)...{RESET}")
    time.sleep(30)
    print(f"{GREEN}✅ Sensor Ready{RESET}")

    connected = connect_to_controller()
    if not connected:
        print(f"{RED}⚠️  Running in OFFLINE Mode{RESET}")

    # PIR state tracking (correct model)
    motion_active = False
    last_motion_time = None
    last_no_motion_sent = None

    last_humidity_read = 0.0

    print(f"{CYAN}👀 Monitoring Started...{RESET}\n")

    try:
        while True:
            now = time.time()

            # ============================
            # PIR MOTION HANDLING (CORRECT)
            # ============================
            motion = pir.motion_detected

            if motion:
                if not motion_active:
                    payload = {
                        "timestamp": ts(),
                        "type": "PIR",
                        "location": LOCATION,
                        "value": "Motion Detected",
                        "status": "Active"
                    }
                    print(f"[{ts()}] {GREEN}🏃 MOTION DETECTED{RESET}")
                    if connected:
                        publish(payload)

                motion_active = True
                last_motion_time = now
                last_no_motion_sent = None

            else:
                if motion_active:
                    motion_active = False
                    last_motion_time = now
                    last_no_motion_sent = None

                if last_motion_time is None:
                    last_motion_time = now

                elapsed = now - last_motion_time

                if last_no_motion_sent is None and elapsed >= NO_MOTION_INTERVAL:
                    payload = {
                        "timestamp": ts(),
                        "type": "PIR",
                        "location": LOCATION,
                        "value": "No Motion",
                        "status": "Inactive",
                        "no_motion_duration": f"{int(elapsed)}s"
                    }
                    print(f"[{ts()}] {YELLOW}zzz No Motion ({int(elapsed)}s){RESET}")
                    if connected:
                        publish(payload)
                    last_no_motion_sent = now

                elif last_no_motion_sent is not None and (now - last_no_motion_sent) >= NO_MOTION_INTERVAL:
                    elapsed = now - last_motion_time
                    payload = {
                        "timestamp": ts(),
                        "type": "PIR",
                        "location": LOCATION,
                        "value": "No Motion",
                        "status": "Inactive",
                        "no_motion_duration": f"{int(elapsed)}s"
                    }
                    print(f"[{ts()}] {YELLOW}zzz No Motion ({int(elapsed)}s){RESET}")
                    if connected:
                        publish(payload)
                    last_no_motion_sent = now

            # ============================
            # HUMIDITY & TEMP SENSOR
            # ============================
            if now - last_humidity_read >= HUMIDITY_READ_INTERVAL:
                last_humidity_read = now
                try:
                    humidity = dht.humidity
                    temperature = dht.temperature

                    if humidity is not None and temperature is not None:
                        payload_hum = {
                            "timestamp": ts(),
                            "type": "Humidity",
                            "location": LOCATION,
                            "value": f"{humidity:.1f}%",
                            "status": "Active"
                        }
                        if connected:
                            publish(payload_hum)

                        payload_temp = {
                            "timestamp": ts(),
                            "type": "Temperature",
                            "location": LOCATION,
                            "value": f"{temperature:.1f}C",
                            "status": "Active"
                        }
                        if connected:
                            publish(payload_temp)

                        # Formatted Output
                        hum_color = BLUE if humidity > 80 else CYAN
                        print(f"[{ts()}] 🌡️  Temp: {temperature:.1f}°C  |  {hum_color}💧 Hum: {humidity:.1f}%{RESET}")
                    else:
                        print(f"[{ts()}] {RED}⚠️  Sensor Read Error (None){RESET}")

                except RuntimeError as e:
                    # Common DHT error, usually ignore it
                    pass 
                except Exception as e:
                    print(f"{RED}❌ Critical Error: {e}{RESET}")
                    dht.exit()
                    raise e

            time.sleep(0.05)

    except KeyboardInterrupt:
        print(f"\n{RED}🛑 Stopping sensors...{RESET}")

    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass
        pir.close()
        dht.exit()

if __name__ == "__main__":
    main()
