#!/usr/bin/env python3
"""
Fixed integrated HR + drowsiness monitor:
- latest_ear/latest_mar are globals so they can be used in the overlay without scope errors.
- safe formatting for N/A values.
"""
import cv2
import dlib
import numpy as np
import threading
import asyncio
import struct
import pygame
import time
import board
import digitalio
import busio
import adafruit_ssd1306
import threading
from datetime import datetime
from bleak import BleakClient, BleakScanner
from imutils import face_utils
from scipy.spatial import distance as dist
from PIL import Image, ImageDraw, ImageFont
from sim808_module import init_sim808, get_gps_location, send_sms, send_special_hr_sms

import sys
import threading
import termios
import tty
import os

quit_flag = False

def key_listener():
    """Listen for a single-key press (non-blocking)."""
    global quit_flag

    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)  # Raw mode = immediate key reads
        while True:
            ch = sys.stdin.read(1)
            if ch.lower() == 'q':
                print("\n[KEY] Quit key pressed!")
                quit_flag = True
                break
    except:
        pass
    finally:
        # Restore terminal mode
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# ===== Fatigue tracking =====
from collections import deque
from datetime import timedelta
fatigue_alarm_times = deque()  # stores timestamps of fatigue alarms
fatigue_lock = threading.Lock()
sms_lock = threading.Lock()
sms_in_progress = False
last_special_sms = None
SPECIAL_SMS_COOLDOWN = timedelta(minutes=30)


# ===== OLED Display Initialization =====
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    oled_width = 128
    oled_height = 64
    oled = adafruit_ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
    OLED_AVAILABLE = True
except Exception as e:
    print(f"[OLED ERROR] {e}")
    OLED_AVAILABLE = False    

# Prepare a blank image for drawing.
image = Image.new("1", (oled_width, oled_height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

def oled_display_text(text):
    if not OLED_AVAILABLE:
        return
    """Display a single line of text on the OLED screen."""
    draw.rectangle((0, 0, oled_width, oled_height), outline=0, fill=0)
    draw.text((5, 25), text, font=font, fill=255)
    oled.image(image)
    oled.show()


# ===== GPIO (LED) Setup =====
led = digitalio.DigitalInOut(board.D26)
led.direction = digitalio.Direction.OUTPUT
led.value = False  # LED OFF


# ===== Audio / alarm setup =====
pygame.mixer.init()
NORMAL_ALARM_FILE = "alarm.mp3"
SPECIAL_ALARM_FILE = "special_alarm.mp3"

alarm_state = None
fatigue_duration = 0
special_alarm_played = False
SPECIAL_ALARM_DURATION = 3  # seconds

def play_alarm_file(file_path, volume=1.0, force=False):
    global alarm_state
    if force:
        pygame.mixer.music.stop()
    if pygame.mixer.music.get_busy() and not force:
        return
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"[Audio Error] {e}")

def stop_alarm():
    global alarm_state
    try:
        pygame.mixer.music.stop()
    except:
        pass
    led.value = False  # LED OFF
    alarm_state = None
    oled_display_text("HELLO! ALL GOOD")
                      
def stop_special_alarm_after_delay(delay=3):
    time.sleep(delay)
    try:
        pygame.mixer.music.stop()
    except:
        pass

def set_alarm_normal(flag_value):
    """
    Start or update the normal fatigue alarm.
    Record ONE timestamp per fatigue *event* by appending only when we transition
    into the normal alarm state (i.e., alarm_state was not "normal").
    """
    global alarm_state, fatigue_alarm_times

    min_vol = 0.2
    max_vol = 1.0
    vol = min_vol + (max_vol - min_vol) * min(flag_value / 50.0, 1.0)

    if alarm_state == "special":
        # Do not start normal alarm if special alarm is active
        return

    now = datetime.now()

    # Only record the fatigue event timestamp when we are transitioning from a non-normal state
    is_transition_to_normal = (alarm_state != "normal")
    with fatigue_lock:
        if is_transition_to_normal:
            fatigue_alarm_times.append(now)
            while fatigue_alarm_times and (now - fatigue_alarm_times[0]) > timedelta(minutes=30):
                fatigue_alarm_times.popleft()
        consecutive_fatigue = len(fatigue_alarm_times) >= 3

    # Start alarm if not already started
    if alarm_state != "normal":
        led.value = True  # LED ON
        play_alarm_file(NORMAL_ALARM_FILE, volume=vol, force=True)
        alarm_state = "normal"
    else:
        # Already playing normal alarm — only adjust volume
        pygame.mixer.music.set_volume(vol)

    # Update OLED display depending on consecutive condition
    if consecutive_fatigue:
        oled_display_text("FATIGUE CONCERN- SEND SMS")
    else:
        oled_display_text("FATIGUE DETECTED")

def set_alarm_special():
    global alarm_state, special_alarm_played

    # Prevent retrigger while HR stays abnormal
    if special_alarm_played:
        return

    led.value = True  # LED ON
    play_alarm_file(SPECIAL_ALARM_FILE, volume=0.1, force=True)

    # Stop after 3 seconds (non-blocking)
    threading.Thread(
        target=stop_special_alarm_after_delay,
        args=(SPECIAL_ALARM_DURATION,),
        daemon=True
    ).start()

    alarm_state = "special"
    special_alarm_played = True
    oled_display_text("HR CONCERN- SEND SMS")


print("Initializing SIM808...")
init_sim808()

# ===== BLE (Heart Rate) Setup =====
HR_MEASUREMENT_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
latest_hr = None
latest_hr_ts = None
hr_lock = threading.Lock()

def handle_hr_data(sender, data: bytearray):
    global latest_hr, latest_hr_ts
    try:
        flags = data[0]
        hr_format = flags & 0x01
        if hr_format == 0:
            hr = data[1]
        else:
            hr = struct.unpack_from("<H", data, 1)[0]
    except Exception as e:
        print(f"[HR parse error] {e}")
        return

    with hr_lock:
        latest_hr = hr
        latest_hr_ts = datetime.now()

    print(f"[{latest_hr_ts}] ❤️ HR: {hr} bpm")
    evaluate_conditions()

async def ble_task():
    print("🔍 Scanning for BLE devices (8s)...")
    devices = await BleakScanner.discover(timeout=8.0)
    if not devices:
        print("No BLE devices found.")
        return

    target = None
    for d in devices:
        if d.name and "HW9" in d.name:
            target = d
            break

    if not target:
        print("❌ HW9 not found during BLE scan.")
        return

    print(f"🔗 Connecting to {target.name} ({target.address}) ...")
    try:
        async with BleakClient(target.address, timeout=30.0) as client:
            if not client.is_connected:
                print("❌ Failed to connect to HW9.")
                return
            print("✅ BLE connected. Subscribing to HR notifications...")
            await client.start_notify(HR_MEASUREMENT_CHAR_UUID, handle_hr_data)
            while True:
                await asyncio.sleep(1)
    except Exception as e:
        print(f"[BLE Error] {e}")

def start_ble_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ble_task())
    except Exception as e:
        print(f"[BLE loop terminated] {e}")
    finally:
        loop.close()

# ===== Face landmarks & detection setup =====
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]
(mStart, mEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["mouth"]

EAR_THRESH = 0.23
MAR_THRESH = 0.85
ear_frame_counter = 0

# Shared EAR/MAR values (accessible outside detection function)
latest_ear = None
latest_mar = None
EAR_drowsy = False
MAR_drowsy = False

def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

def mouth_aspect_ratio(mouth):
    A = dist.euclidean(mouth[2], mouth[10])
    B = dist.euclidean(mouth[4], mouth[8])
    C = dist.euclidean(mouth[0], mouth[6])
    return (A + B) / (2.0 * C)

def detect_drowsiness_on_frame(frame):
    """Detect EAR & MAR, annotate frame, update global latest_ear/latest_mar/EAR_drowsy/MAR_drowsy."""
    global EAR_drowsy, MAR_drowsy, ear_frame_counter, latest_ear, latest_mar

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rects = detector(gray, 0)

    # default when no face found
    EAR_drowsy_local = False
    MAR_drowsy_local = False
    ear_val = None
    mar_val = None

    for rect in rects:
        shape = predictor(gray, rect)
        shape = face_utils.shape_to_np(shape)

        leftEye = shape[lStart:lEnd]
        rightEye = shape[rStart:rEnd]
        mouth = shape[mStart:mEnd]

        # compute EAR
        leftEAR = eye_aspect_ratio(leftEye)
        rightEAR = eye_aspect_ratio(rightEye)
        ear_val = (leftEAR + rightEAR) / 2.0

        # mouth safety check
        if mouth.shape[0] >= 11:
            mar_val = mouth_aspect_ratio(mouth)
            MAR_drowsy_local = mar_val > MAR_THRESH
        else:
            mar_val = None
            MAR_drowsy_local = False

        # EAR temporal
        if ear_val is not None:
            if ear_val < EAR_THRESH:
                ear_frame_counter += 1
            else:
                ear_frame_counter = 0
            EAR_drowsy_local = ear_frame_counter >= 10

        # draw annotations
        cv2.drawContours(frame, [cv2.convexHull(leftEye)], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [cv2.convexHull(rightEye)], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [cv2.convexHull(mouth)], -1, (0, 255, 0), 1)

        break  # process only first face

    # update globals
    latest_ear = ear_val
    latest_mar = mar_val
    EAR_drowsy = EAR_drowsy_local
    MAR_drowsy = MAR_drowsy_local

    return frame

# ===== Evaluation logic =====
def evaluate_conditions():
    global latest_hr, alarm_state, fatigue_duration

    with hr_lock:
        hr = latest_hr

    # Special alarm: HR <60 or >120
    if hr is not None:
        if hr < 60 or hr > 120:
            set_alarm_special()
            return

    # Normal fatigue logic:
    # EAR OR MAR OR (HR <81.5 AND EAR) OR (HR <81.5 AND MAR)
    normal = False
    if EAR_drowsy or MAR_drowsy:
        normal = True
    elif hr is not None and hr < 81.5 and (EAR_drowsy or MAR_drowsy):
        normal = True

    if normal:
        fatigue_duration += 1
        set_alarm_normal(fatigue_duration)
    else:
        fatigue_duration = 0
        stop_alarm()
            
        # Reset special alarm once HR is normal again
        global special_alarm_played
        special_alarm_played = False

# ===== Send SMS if drowsiness>3 in <30mins =====
def check_and_send_sms():
    global fatigue_alarm_times, sms_in_progress

    with sms_lock:
        if sms_in_progress:
            return

        sms_in_progress = True

    print("\n🚨 CONSECUTIVE DROWSINESS DETECTED — Sending SMS...")

    lat, lon = get_gps_location()

    if lat and lon:
        msg = (
            "Driver fatigue detected! Please check up and monitor the driver. "
            f"Location: https://maps.google.com/?q={lat},{lon}"
        )
    else:
        msg = "Driver fatigue detected! Please check up and monitor the driver."

    success = send_sms("+639190998798", msg)

    with sms_lock:
        if success:
            print("📨 SMS SENT. Clearing fatigue history.")
            with fatigue_lock:
                fatigue_alarm_times.clear()
        else:
            print("📨 SMS sent. Clearing fatigue history.")
            with fatigue_lock:
                fatigue_alarm_times.clear()

        sms_in_progress = False

listener_thread = threading.Thread(target=key_listener, daemon=True)
listener_thread.start()

print("Press 'q' to quit program.")

# ===== Main (start BLE thread then camera loop) =====
def main():
    global last_special_sms

    ble_thread = threading.Thread(target=start_ble_background, daemon=True)
    ble_thread.start()
    time.sleep(1.0)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Unable to open camera. Check camera connection.")
        return

    try:
        while True:
            if quit_flag:
                print("Shutting down program...")
                break

            ret, frame = cap.read()
            if not ret:
                print("Frame read failed; exiting.")
                break

            frame = cv2.rotate(frame, cv2.ROTATE_180)
            frame = detect_drowsiness_on_frame(frame)

            # overlay HR and alarm info (safe formatting)
            with hr_lock:
                hr_display = latest_hr

            ear_text = f"{latest_ear:.2f}" if latest_ear is not None else "N/A"
            mar_text = f"{latest_mar:.2f}" if latest_mar is not None else "N/A"

            h, w = frame.shape[:2]
            cv2.rectangle(frame, (5, h - 70), (320, h - 5), (0, 0, 0), -1)
            cv2.putText(frame,
                        f"EAR:{ear_text} {'Y' if EAR_drowsy else 'N'}  MAR:{mar_text} {'Y' if MAR_drowsy else 'N'}",
                        (10, h - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            if hr_display is not None:
                hr_color = (0, 200, 255) if not (hr_display < 60 or hr_display > 120) else (0, 0, 255)
                cv2.putText(frame, f"HR: {hr_display} bpm", (10, h - 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, hr_color, 2)

            if alarm_state == "special":
                cv2.putText(frame, "SPECIAL ALARM (ABNORMAL HR)", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                # --- Send special HR SMS (once per event) ---
                now = datetime.now()

                with sms_lock:
                    if (last_special_sms is None or
                        (now - last_special_sms) > SPECIAL_SMS_COOLDOWN):

                        if latest_hr is not None:
                            threading.Thread(
                                target=send_special_hr_sms,
                                args=("+639190998798", latest_hr),
                                daemon=True
                            ).start()

                            last_special_sms = now

            elif alarm_state == "normal":
                cv2.putText(frame, "FATIGUE ALARM", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            
            # Check if 3+ fatigue alarms in <30 min
            if len(fatigue_alarm_times) >= 3:
                first_time = fatigue_alarm_times[0]
                if (datetime.now() - first_time) < timedelta(minutes=30):
                    cv2.putText(frame, "CONSECUTIVE DROWSINESS!!", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # Launch SMS send in background thread (non-blocking)
                    if not sms_in_progress:
                        threading.Thread(target=check_and_send_sms, daemon=True).start()

            cv2.imshow("Driver Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # periodically re-evaluate (in case HR-only changes)
            evaluate_conditions()

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        stop_alarm()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()