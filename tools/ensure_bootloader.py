#!/usr/bin/env python3
import serial
import time
import sys
import argparse

def reset_esp32(port):
    """
    Force a hardware reset pulse on the ESP32 to enter bootloader mode.
    GPIO0 (RTS) must be LOW while EN (DTR) is pulsed.
    """
    try:
        # Opening at 115200 for stability on macOS
        ser = serial.Serial(port, 115200)
        
        print(f"--- Software Reset Sequence on {port} ---")
        
        # 1. State: EN=High, GPIO0=High
        ser.setDTR(False)
        ser.setRTS(False)
        time.sleep(0.1)
        
        # 2. State: GPIO0=Low (RTS down)
        ser.setRTS(True)
        time.sleep(0.1)
        
        # 3. State: EN=Low (DTR down) -> This resets the chip
        ser.setDTR(True)
        time.sleep(0.2)
        
        # 4. State: EN=High (DTR back up) -> Chip boots with GPIO0=Low
        ser.setDTR(False)
        time.sleep(0.5)
        
        # 5. Release GPIO0
        ser.setRTS(False)
        
        ser.close()
        print("Success: ESP32 should now be in Download Mode.")
        return True
    except Exception as e:
        print(f"Error during reset: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    args = parser.parse_args()
    
    if not reset_esp32(args.port):
        sys.exit(1)
