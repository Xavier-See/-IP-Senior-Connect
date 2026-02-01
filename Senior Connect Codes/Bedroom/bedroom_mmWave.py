import serial
import time
import json
import paho.mqtt.client as mqtt

# ==============================
# 👇 CONFIGURATION
# ==============================
SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 115200

# MQTT SETTINGS
BROKER_ADDRESS = "raspberrypi.local"
TOPIC = "senior_connect/sensors/mmwave_bedroom"

# ==============================

# ----- MQTT SETUP -----
client = mqtt.Client()

def connect_mqtt():
    try:
        client.connect(BROKER_ADDRESS, 1883, 60)
        client.loop_start()
        print(f"✅ Connected to Controller at {BROKER_ADDRESS}")
        return True
    except Exception as e:
        print(f"🔴 MQTT Connection Failed: {e}")
        return False

def publish_status(status_msg, status_code, heart=0, breath=0):
    payload = {
        "type": "mmWave",
        "location": "Bedroom",
        "value": status_msg,        # "In Bed", "Out of Bed"
        "status": status_code,      # "Occupied", "Empty"
        "heart_rate": int(heart),
        "breath_rate": int(breath)
    }
    
    try:
        client.publish(TOPIC, json.dumps(payload))
        print(f"📡 SENT: {status_msg} (HR: {heart}, BR: {breath})")
    except:
        print("⚠️ MQTT Publish Error")

# ----- MAIN SENSOR LOOP -----
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.5)
print("=== BEDROOM SLEEP MONITOR STARTED ===")

connected = connect_mqtt()

# State Tracking
in_bed_state = None 
last_heart_rate = 0
last_breath_rate = 0

try:
    while True:
        data = ser.read(128)
        
        if data:
            # Check for C1001 Header (0x53 0x59)
            if len(data) >= 10 and data[0] == 0x53 and data[1] == 0x59:
                report_type = data[3]
                
                # --- REPORT 0x01: PRESENCE / BED ENTRY ---
                if report_type == 0x01:
                    current_status = data[6] # 0x00=Out, 0x01=In
                    
                    if current_status != in_bed_state:
                        if current_status == 0x01:
                            print("\n🛏️ User Entered Bed")
                            if connected: publish_status("In Bed", "Occupied")
                        
                        elif current_status == 0x00:
                            print("\n🚪 User Exited Bed")
                            # Reset vitals on exit
                            last_heart_rate = 0
                            last_breath_rate = 0
                            if connected: publish_status("Out of Bed", "Empty", 0, 0)
                        
                        in_bed_state = current_status

                # --- REPORT 0x03: VITALS (Only if in bed) ---
                elif report_type == 0x03 and in_bed_state == 0x01:
                    breath_rate = data[6]
                    heart_rate = data[7]
                    
                    # Only publish if values change (reduces spam)
                    if breath_rate != last_breath_rate or heart_rate != last_heart_rate:
                        print(f"💓 Vitals: HR={heart_rate} | BR={breath_rate}")
                        if connected: 
                            publish_status("In Bed", "Occupied", heart_rate, breath_rate)
                        
                        last_heart_rate = heart_rate
                        last_breath_rate = breath_rate

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n🛑 Stopping Bedroom Monitor...")

finally:
    ser.close()
    client.loop_stop()
    client.disconnect()
