import asyncio
from bleak import BleakScanner

async def check():
    print("\n--- WAVEFORM PRO BLE SCANNER ---")
    print("Searching for 'WaveForm_EEG_Pro' (5sec)...")
    
    device = await BleakScanner.find_device_by_name("WaveForm_EEG_Pro", timeout=5.0)
    
    if device:
        print(f"✅ SUCCESS: Device Found!")
        print(f"Name: {device.name}")
        print(f"Address: {device.address}")
        print(f"RSSI: {device.rssi}")
        print("\nYour Mac sees the 'Pro' signal. You can now use the dashboard or mobile app.")
    else:
        print("❌ FAILED: Device not found.")
        print("Check if:")
        print("1. Your ESP32 is powered on (Red LED).")
        print("2. You are within 1-2 meters of the device.")
        print("3. Bluetooth is ON in System Settings.")

if __name__ == "__main__":
    asyncio.run(check())
