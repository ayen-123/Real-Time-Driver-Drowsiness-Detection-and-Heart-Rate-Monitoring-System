import serial
import time
import re

PORT = "/dev/ttyAMA0"
BAUD = 9600

ser = None

def send_at(command, expected_response="OK", timeout=3):
    ser.write((command + "\r\n").encode())
    time.sleep(0.3)
    end = time.time() + timeout
    buf = b""
    while time.time() < end:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting)
            if expected_response.encode() in buf:
                break
    print(f">>> {command}")
    print(buf.decode(errors="ignore"))
    return expected_response.encode() in buf


def check_gps_status():
    ser.write(b"AT+CGPSSTATUS?\r\n")
    time.sleep(1)
    resp = ser.read_all().decode(errors="ignore")
    m = re.search(r"Status:\s*(.+)", resp)
    return m.group(1).strip() if m else "Unknown"


def get_gps_location():
    """Long retry loop + status logging."""
    print("\n--- Activating GPS ---")
    send_at("AT+CGNSPWR=1")
    time.sleep(2)

    print("⏳ Waiting for GPS fix...\n")
    for i in range(3): 
        ser.write(b"AT+CGNSINF\r\n")
        time.sleep(1)
        resp = ser.read_all().decode(errors="ignore")
        print(resp.strip())

        status = check_gps_status()
        print(f"[Attempt {i+1}/3] GPS Status: {status}")

        m = re.search(r"\+CGNSINF: 1,1,\d+,([\d\.\-]+),([\d\.\-]+)", resp)
        if m:
            print("\n✅ GPS FIX ACQUIRED!")
            lat, lon = m.group(1), m.group(2)
            print(f"📍 {lat}, {lon}")
            return lat, lon

        time.sleep(3)

    print("❌ GPS fix failed")
    return None, None


def send_sms(phone, message):
    print(f"\n--- Sending SMS to {phone} ---")
    send_at("AT+CMGF=1")   # text mode
    ser.write(f'AT+CMGS="{phone}"\r'.encode())
    time.sleep(1)
    ser.write(message.encode() + b"\x1A")
    time.sleep(3)
    print(ser.read_all().decode(errors="ignore"))


def init_sim808():
    """Call ONCE at program start."""
    global ser
    print("🔌 Initializing SIM808...")

    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)

    if not send_at("AT"):
        print("❌ SIM808 not responding!")
        return False

    send_at("ATE0")
    send_at("AT+CSQ")
    send_at("AT+CCID")
    send_at("AT+CREG?")
    return True

def send_special_hr_sms(phone, hr):
    """
    Sends a dangerous heart rate SMS with GPS location.
    """
    lat, lon = get_gps_location()

    if lat and lon:
        msg = (
            f"Dangerous driver heart rate detected. "
            f"Heart rate is {hr} BPM."
            f"Please check up and monitor the driver."
            f"Location: https://maps.google.com/?q={lat},{lon}"
        )
    else:
        msg = (
            f"Dangerous driver heart rate detected. "
            f"Heart rate is {hr} BPM. "
            f"Please check up and monitor the driver."
        )

    send_sms(phone, msg)