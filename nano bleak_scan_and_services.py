import asyncio
from bleak import BleakScanner, BleakClient

async def main():
    print("🔍 Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=8.0)

    if not devices:
        print("❌ No BLE devices found. Make sure your band is nearby and not connected to a phone.")
        return

    print("\n📋 Found devices:")
    for i, d in enumerate(devices):
        print(f"[{i}] {d.name} - {d.address}")

    choice = input("\n👉 Enter the number of your Mi Band device: ")
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

            print("\n📡 Listing GATT services and characteristics...")
            for service in client.services:
                print(f"Service: {service.uuid} ({service.description})")
                for char in service.characteristics:
                    props = ",".join(char.properties)
                    print(f"  Characteristic: {char.uuid} ({char.description}) | Properties: {props}")

            print("\n✅ Done. Look for UUID `0000180d` (Heart Rate Service) and `00002a37` (Heart Rate Measurement).")

    except Exception as e:
        print(f"❌ Error while connecting: {e}")
        print("💡 Tips:")
        print("  1. Make sure the Mi Band is not connected to your phone.")
        print("  2. Try pairing manually with `bluetoothctl` before running this script.")
        print("  3. Keep the band awake (move/tap the screen).")

if __name__ == "__main__":
    asyncio.run(main())