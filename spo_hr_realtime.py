#!/usr/bin/env python3
import asyncio
import struct
from bleak import BleakClient, BleakScanner

# Heart Rate Service + Characteristic UUIDs
HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def handle_hr_data(sender, data: bytearray):
    """Callback when heart rate measurement notifications arrive."""
    flags = data[0]
    hr_format = flags & 0x01
    if hr_format == 0:
        heart_rate = data[1]
    else:
        heart_rate = struct.unpack_from("<H", data, 1)[0]

    print(f"❤️ Heart Rate: {heart_rate} bpm")

async def main():
    print("🔍 Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=8.0)

    if not devices:
        print("❌ No BLE devices found.")
        return

    print("\n📋 Found devices:")
    for i, d in enumerate(devices):
        print(f"[{i}] {d.name or 'Unnamed'} - {d.address}")

    choice = input("\n👉 Enter device number for your HW9: ")
    try:
        device = devices[int(choice)]
    except Exception:
        print("❌ Invalid choice.")
        return

    print(f"\n🔗 Connecting to {device.name} ({device.address})...")

    try:
        async with BleakClient(device.address, timeout=30.0) as client:
            if not client.is_connected:
                print("❌ Failed to connect.")
                return
            print("✅ Connected!")

            print("[📡] Subscribing to Heart Rate Measurement...")
            await client.start_notify(HR_MEASUREMENT_CHAR_UUID, handle_hr_data)

            print("⏳ Streaming heart rate data. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
