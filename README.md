# Real-Time-Driver-Drowsiness-Detection-and-Heart-Rate-Monitoring-System


## Introduction
Driver fatigue is one of the leading causes of road accidents worldwide, particularly among taxi drivers who often work long and irregular hours. This project presents a real-time driver monitoring system that combines computer vision and physiological monitoring to identify signs of drowsiness before they lead to accidents. The system utilizes facial feature analysis through Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR), alongside heart rate monitoring from a wearable device, to assess the driver's condition. Upon detecting fatigue, the system immediately alerts the driver and escalates repeated incidents to taxi fleet operators through SMS notifications. The goal of the project is to improve road safety, reduce fatigue-related accidents, and provide fleet operators with an additional layer of driver monitoring and intervention.


## Technologies Used
- Python
- OpenCV
- Dlib
- NumPy
- Raspberry Pi 5
- Xiaomi Smart Band 9 Active
- Bluetooth Low Energy (BLE)
- Haar Cascade Classifier
- Eye Aspect Ratio (EAR)
- Mouth Aspect Ratio (MAR)
- SMS API / GSM Module
- Linux (Raspberry Pi OS)


## Features

### 👁️ Real-Time Eye Monitoring
The system continuously analyzes the driver's eyes using facial landmark detection. Eye Aspect Ratio (EAR) is computed for every frame to determine whether the driver's eyes remain closed beyond the defined threshold.

### 😮 Yawn Detection
Using Mouth Aspect Ratio (MAR), the system detects prolonged mouth opening associated with yawning, which is a common indicator of fatigue and reduced alertness.

### ❤️ Heart Rate Monitoring
A Xiaomi Smart Band 9 Active continuously records the driver's heart rate and transmits the data to the Raspberry Pi through Bluetooth Low Energy (BLE).

### 🚨 Drowsiness Alert System
When signs of fatigue are detected through facial analysis or physiological indicators, an audible alarm immediately alerts the driver to regain attention.

### 📱 SMS Notification to Fleet Operators
If the system repeatedly detects drowsiness events within a specified period, an SMS notification containing the alert details is sent directly to the taxi fleet operator.

### 📊 Multimodal Fatigue Detection
Unlike conventional systems that rely on a single input, this project combines behavioral indicators (eye closure and yawning) with physiological indicators (heart rate) to improve detection reliability.

### 🚖 Fleet Safety Monitoring
The system extends beyond individual driver alerts by providing fleet operators with information that enables proactive intervention and enhanced operational safety.


## Process/Architecture

The system begins by initializing the camera and wearable heart rate monitoring device. Once both devices are connected and operational, the camera continuously captures video frames of the driver while the smartwatch streams heart rate data to the Raspberry Pi.

Using OpenCV and Dlib, the system detects the driver's face and extracts facial landmarks. These landmarks are used to calculate Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR), which serve as indicators of eye closure and yawning behavior. Simultaneously, heart rate readings are evaluated against predefined thresholds.

The system continuously processes all inputs in real time. If the driver's eyes remain closed for a prolonged period, if excessive yawning is detected, or if heart rate patterns indicate possible fatigue, the system classifies the driver as drowsy and immediately activates an alarm.

Every drowsiness event is logged by the system. If the number of drowsiness alerts exceeds a predefined threshold within a monitoring period, an SMS notification is sent to the taxi fleet operator. This notification serves as an escalation mechanism, allowing management to intervene before a fatigue-related accident occurs.

The monitoring process continues as long as the vehicle remains operational, ensuring continuous observation of the driver's condition throughout the trip.



## How to Run the Project

1. Clone the Repository
2. Create a Virtual Environment

```bash
python -m venv venv
```

3. Activate the Virtual Environment

For Windows:

```bash
venv\Scripts\activate
```

For Linux/Raspberry Pi:

```bash
source venv/bin/activate
```

4. Install Required Dependencies

```bash
pip install -r requirements.txt
```

5. Connect the Camera

Attach a USB camera or Raspberry Pi Camera Module and verify that it is detected by the operating system.

6. Pair the Xiaomi Smart Band 9 Active

Use Bluetooth Low Energy (BLE) tools or the project's connection script to establish communication between the smartwatch and Raspberry Pi.

7. Configure SMS Notifications

Update the SMS configuration file with the required API credentials or GSM module settings.

Example:

```python
PHONE_NUMBER = "+63XXXXXXXXXX"
API_KEY = "YOUR_API_KEY"
```

8. Start the Monitoring System

```bash
python main.py
```

9. Observe Real-Time Monitoring

The system will begin:

- Detecting facial landmarks
- Computing EAR and MAR values
- Monitoring heart rate data
- Triggering alarms when necessary
- Sending SMS alerts upon repeated drowsiness detection

10. Stop the System

Press:

```bash
CTRL + Q
```

to safely terminate the application.

---

## Future Improvements

- GPS integration for real-time location reporting
- Cloud-based fleet monitoring dashboard
- Machine learning-based personalized fatigue thresholds
- Driver identification and authentication
- Infrared camera support for low-light environments
- Mobile application for fleet operators


## Researchers

This project was developed as an undergraduate thesis entitled **"A Real-Time Driver Drowsiness Detection and Heart Rate Monitoring System for Taxi Fleets"**. The study focuses on enhancing road safety through multimodal fatigue detection, combining computer vision and physiological monitoring techniques to provide both driver-level and fleet-level interventions.


## License

This project is intended for academic and research purposes. Feel free to use, modify, and extend the system with proper attribution.
