import time
import threading
import subprocess
import os
import sys
import glob
import json
import numpy as np
from collections import deque
from scipy.fftpack import fft
from scipy.signal import butter, lfilter, iirnotch

try:
    import serial
    import serial.tools.list_ports
    import asyncio
    from bleak import BleakScanner, BleakClient
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False

# ──────────────────────────────────────────────────────────────
# CORE UTILS
# ──────────────────────────────────────────────────────────────

def list_serial_ports() -> list:
    """Return list of connected USB/Serial devices."""
    if not SERIAL_OK: return []
    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append({
            "port": p.device,
            "description": p.description or "Unknown",
            "is_arduino": any(kw in (p.description or "").lower() for kw in ("arduino", "usb serial", "cp2102", "ch340", "esp32")),
        })
    return ports

def list_bluetooth_devices() -> list:
    """Return paired BT devices (macOS-specific)."""
    devices = []
    if sys.platform == "darwin":
        try:
            out = subprocess.check_output(["system_profiler", "SPBluetoothDataType", "-json"], timeout=2).decode()
            data = json.loads(out)
            bt_info = data.get("SPBluetoothDataType", [{}])[0]
            for key in ["device_title", "device_connected", "device_not_connected"]:
                items = bt_info.get(key, [])
                if isinstance(items, list):
                    for entry in items:
                        for name, info in entry.items():
                            if isinstance(info, dict):
                                addr = info.get("device_address")
                                if addr: devices.append({"name": name, "address": addr})
        except Exception:
            pass
    devices.append({"name": "Enter manually...", "address": ""})
    return devices

# ──────────────────────────────────────────────────────────────
# SIGNAL ENGINE
# ──────────────────────────────────────────────────────────────

class SignalEngine:
    BANDS = {
        "delta": (0.5, 4),   "theta": (4, 8),
        "alpha": (8, 12),  "beta":  (13, 30),
        "gamma": (30, 45),
    }

    def __init__(self, fs: int = 200, buffer_size: int = 400, demo: bool = True):
        self.fs          = fs
        self.buffer_size = buffer_size
        self.demo        = demo
        self.port: str   = ""
        
        self._buf        = deque(maxlen=buffer_size)
        self._filtered   = np.zeros(buffer_size)
        self._band_waves = {k: np.zeros(buffer_size) for k in self.BANDS}
        
        # State
        self._ser          = None
        self._ser_lock     = threading.Lock()
        self.adc_max       = 32767  # Default 16-bit
        self.board_type    = "ESP32"
        self.last_val: float = 0.0
        self._is_bt_bridge = False
        self.connection_error: str = ""
        self._ble_client = None
        self._loop = asyncio.new_event_loop()
        self._data_lock = threading.Lock()
        
        # UUIDs match the Pro Mission Code (iPhone 17 Pro Optimized)
        self.UART_SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
        self.UART_TX_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

    # --- Connection Methods ---

    def connect(self, port: str, baud: int = 115200):
        """Unified connection method for Serial/USB."""
        self.connect_serial(port, baud)

    def connect_serial(self, port: str, baud: int = 115200):
        """Connect via USB Serial or macOS BT Bridge."""
        self.disconnect()
        try:
            with self._ser_lock:
                # Use longer timeout for Bluetooth ports (SPP is slower)
                timeout = 0.5 if ("cu." in port or "WaveForm" in port) else 0.05
                self._ser = serial.Serial(port, baud, timeout=timeout)
                self.port = port
                self.demo = False
                self.connection_error = ""
                self._is_bt_bridge = any(kw in port for kw in ["WaveForm", "EEG", "Connect", "ESP32"])
                time.sleep(1.0) # wait for boot
                self._parse_handshake()
        except Exception as e:
            self.connection_error = str(e)
            self.demo = True

    def connect_bluetooth(self, address: str = ""):
        """Connect to Stealth BLE Keyboard. Bypass OS block."""
        threading.Thread(target=self._run_ble_loop, daemon=True).start()

    def _run_ble_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._ble_manager())

    async def _ble_manager(self):
        self.demo = False
        try:
            device = await BleakScanner.find_device_by_filter(
                lambda d, ad: "WaveForm" in (d.name or "") or self.UART_SERVICE_UUID.lower() in ad.service_uuids
            )
            if not device:
                self.connection_error = "Stealth device not found."
                self.demo = True
                return

            self.port = device.address
            async with BleakClient(device) as client:
                self._ble_client = client
                self._is_bt_bridge = True
                await client.start_notify(self.UART_TX_CHAR_UUID, self._ble_callback)
                while self._is_bt_bridge:
                    await asyncio.sleep(1)
        except Exception as e:
            self.connection_error = str(e)
            self.demo = True

    def _ble_callback(self, sender, data):
        try:
            line = data.decode().strip()
            if line and line.isdigit():
                val = (float(line) / self.adc_max) * 1023.0
                with self._data_lock:
                    self._buf.append(val)
                    self.last_val = val
        except: pass

    def disconnect(self):
        self._is_bt_bridge = False
        with self._ser_lock:
            if self._ser and self._ser.is_open:
                self._ser.close()
            self._ser = None
        self.demo = True

    @property
    def is_connected(self):
        return (not self.demo) and ((self._ser is not None and self._ser.is_open) or self._is_bt_bridge)

    @property
    def connection_type(self):
        if not self.is_connected: return "demo"
        return "bluetooth" if self._is_bt_bridge else "usb"

    # --- Handshake ---

    def _parse_handshake(self):
        if not self.is_connected: return
        deadline = time.time() + 2.0
        while time.time() < deadline:
            try:
                line = self._ser.readline().decode("ascii", errors="ignore").strip()
                if line.startswith("ADC_MAX:"):
                    self.adc_max = int(line.split(":")[1])
                elif line.startswith("FS:"):
                    self.fs = int(line.split(":")[1])
                elif line and line.isdigit():
                    break
            except Exception: break

    # --- Data Processing ---

    def tick(self, samples_per_tick: int = 15):
        """Read fresh samples and refresh filtered wave."""
        new_samples: list[float] = []
        if not self.is_connected:
            # DEMO MODE: Generate sinewaves + noise
            t = time.time()
            for _ in range(samples_per_tick):
                val = 512 + 100 * np.sin(2 * np.pi * 10 * t) + np.random.normal(0, 10)
                new_samples.append(val)
                t += 1.0/self.fs
            for s in new_samples:
                self._buf.append(s)
                self.last_val = s
        elif self._ser:
            with self._ser_lock:
                for _ in range(samples_per_tick * 2):
                    if len(new_samples) >= samples_per_tick: break
                    try:
                        line = self._ser.readline().decode("ascii", errors="ignore").strip()
                        if line and line.lstrip("-").isdigit():
                            val = float(line)
                            # Normalize to 0-1023 for uniform plotting
                            val = (val / self.adc_max) * 1023.0
                            new_samples.append(val)
                    except serial.SerialException as e:
                        self.connection_error = f"Link Lost: {str(e)}"
                        self.disconnect()
                        break
                    except Exception: break
        
        for s in new_samples:
            self._buf.append(s)
            self.last_val = s
        
        if len(self._buf) >= self.buffer_size:
            arr = np.array(self._buf)
            # 1. Bandpass 0.5-45Hz
            self._filtered = self._bandpass(arr, 0.5, 45)
            # 2. Notch 50Hz (mains hum)
            self._filtered = self._notch(self._filtered, 50)
            
            # 3. Bandwaves
            for name, (lo, hi) in self.BANDS.items():
                self._band_waves[name] = self._bandpass(arr, lo, hi)

    # --- DSP ---

    def _bandpass(self, data, lo, hi, order=4):
        nyq = 0.5 * self.fs
        b, a = butter(order, [lo/nyq, hi/nyq], btype='band')
        return lfilter(b, a, data)

    def _notch(self, data, freq, q=30):
        nyq = 0.5 * self.fs
        b, a = iirnotch(freq/nyq, q)
        return lfilter(b, a, data)

    def get_waveform(self): return self._filtered
    def get_band_waveform(self, name): return self._band_waves.get(name, np.zeros(self.buffer_size))
    
    def get_fft(self):
        if len(self._filtered) == 0: return np.array([]), np.array([])
        v = np.abs(fft(self._filtered))
        f = np.fft.fftfreq(len(v), 1/self.fs)
        pos = f > 0
        return f[pos], v[pos]

    def get_bands(self):
        """Estimate band powers (simplified sum)."""
        ret = {}
        for name in self.BANDS:
            ret[name] = np.mean(np.abs(self._band_waves[name])) * 2
        return ret

    def get_stress_index(self):
        b = self.get_bands()
        return b["beta"] / (b["alpha"] + 0.1)

    def get_brain_state(self):
        s = self.get_stress_index()
        if s < 1.2: return "Relaxed", "😌", "#10b981"
        if s < 2.5: return "Focused", "🧠", "#2563eb"
        return "Stressed", "😰", "#ef4444"
