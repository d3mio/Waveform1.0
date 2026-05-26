#!/usr/bin/env python3
"""
tools/esp32_flash.py  –  WaveForm ESP32 Firmware Flasher
=========================================================
This script uploads the WaveForm EEG firmware to an ESP32 DevKit V1. 
It performs a custom "triple-pulse" reset sequence to force the chip into 
Download Mode, which is much more reliable on macOS than standard esptool resets.

Usage:
  python3 tools/esp32_flash.py --port /dev/cu.usbserial-0001 --build /tmp/waveform_build
"""

import sys
import os
import time
import subprocess
import argparse

# Check for pyserial
try:
    import serial
except ImportError:
    print("pyserial not found, installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyserial"])
    import serial

def flash_esp32(port, build_dir, baud=115200):
    bin_main = os.path.join(build_dir, "waveform_eeg_bridge.ino.bin")
    bin_boot = os.path.join(build_dir, "waveform_eeg_bridge.ino.bootloader.bin")
    bin_part = os.path.join(build_dir, "waveform_eeg_bridge.ino.partitions.bin")
    
    # Common location for boot_app0.bin (ESP32 core 2.x)
    bin_app0 = os.path.expanduser("~/Library/Arduino15/packages/esp32/hardware/esp32/2.0.14/tools/partitions/boot_app0.bin")
    if not os.path.exists(bin_app0):
        # Fallback search or just use a generic path if we can find it
        bin_app0 = None
        # Try to find it in the build dir if arduino-cli put it there
        if os.path.exists(os.path.join(build_dir, "boot_app0.bin")):
            bin_app0 = os.path.join(build_dir, "boot_app0.bin")

    print(f"\n🚀 Preparing to flash WaveForm firmware to {port}...")
    
    # 1. TRIPLE-PULSE RESET (The macOS Special)
    # This sequence is much "sticker" than the default esptool one.
    try:
        ser = serial.Serial(port, baud)
        print("  - Triggering custom reset sequence...")
        for _ in range(3):
            ser.setRTS(True)   # GPIO0 LOW
            ser.setDTR(False)  # EN HIGH
            time.sleep(0.05)
            ser.setDTR(True)   # EN LOW (Reset)
            time.sleep(0.1)
            ser.setDTR(False)  # EN HIGH (Release Reset)
            time.sleep(0.05)
        
        # Hold GPIO0 low for a moment while esptool starts
        ser.setRTS(True) 
        time.sleep(0.2)
        ser.close()
    except Exception as e:
        print(f"  ✗ Error opening port for reset: {e}")
        return False

    # 2. RUN ESPTOOL
    # We use --before no_reset because we just did it manually.
    cmd = [
        sys.executable, "-m", "esptool",
        "--chip", "esp32",
        "--port", port,
        "--baud", str(baud),
        "--before", "no_reset",
        "--after", "hard_reset",
        "write_flash", "-z",
        "--flash_mode", "dio",
        "--flash_freq", "80m",
        "--flash_size", "detect",
        "0x1000", bin_boot,
        "0x8000", bin_part,
        "0x10000", bin_main
    ]
    
    # Add boot_app0 if found
    if bin_app0:
        cmd.extend(["0xe000", bin_app0])
    
    print(f"  - Starting upload via esptool...")
    result = subprocess.run(cmd)
    return result.returncode == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-0001")
    parser.add_argument("--build", default="/tmp/waveform_build")
    args = parser.parse_args()
    
    if flash_esp32(args.port, args.build):
        print("\n✅ Upload Complete! Enjoy your brainwaves.")
        sys.exit(0)
    else:
        print("\n❌ Upload Failed. Double-check your USB connection.")
        sys.exit(1)
