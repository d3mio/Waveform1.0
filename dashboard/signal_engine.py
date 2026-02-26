"""
signal_engine.py – WaveForm EEG Signal Engine
==============================================
Supports two modes:
  DEMO   – synthesises realistic multi-band EEG (no hardware needed)
  LIVE   – reads raw ADC values from an Arduino/ESP32 over USB serial

Serial Protocol (sent by waveform_eeg_bridge.ino)
--------------------------------------------------
  Startup handshake (once):
      WAVEFORM_START
      ADC_MAX:<int>          e.g. 4095 for ESP32, 1023 for AVR
      FS:<int>               e.g. 200

  Per-sample (200 Hz):
      <integer>              raw ADC value

  Diagnostics (every ~1 s):
      RATE:<ms>              elapsed ms for last 200 samples (should be ~1000)
"""

import numpy as np
from collections import deque
from scipy.signal import butter, lfilter, iirnotch
from scipy.fft import fft
import random
import time
import threading

try:
    import serial
    import serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False


# ──────────────────────────────────────────────────────────────
# Port scanner
# ──────────────────────────────────────────────────────────────

def list_serial_ports() -> list:
    if not SERIAL_OK:
        return []
    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append({
            "port":        p.device,
            "description": p.description or "Unknown",
            "hwid":        p.hwid or "",
            "is_arduino":  any(kw in (p.description or "").lower()
                               for kw in ("arduino", "ch340", "ch341",
                                          "ft232", "cp210", "esp32",
                                          "usb serial", "uart")),
        })
    return ports


# ──────────────────────────────────────────────────────────────
# Signal Engine
# ──────────────────────────────────────────────────────────────

class SignalEngine:

    BANDS = {
        "delta": (0.5,  4),
        "theta": (4,    8),
        "alpha": (8,   12),
        "beta":  (13,  30),
        "gamma": (30,  45),
    }

    def __init__(self, fs: int = 200, buffer_size: int = 400,
                 port: str = None, baud: int = 115200, demo: bool = True):
        self.fs          = fs
        self.buffer_size = buffer_size
        self.demo        = demo
        self.port        = port
        self.baud        = baud

        self._buf      = deque(maxlen=buffer_size)
        self._filtered = np.zeros(buffer_size)
        self._t        = 0.0
        self._dt       = 1.0 / fs

        # Serial state
        self._ser          = None
        self._serial_lock  = threading.Lock()
        self._serial_error = None

        # Data accuracy diagnostics
        self.adc_max        = 1023      # updated from handshake
        self.board_type     = "AVR"     # or "ESP32"
        self.reported_rate  = None      # ms reported by RATE: line
        self.sample_rate_ok = True

        # Demo mood cycles: Relaxed → Focused → Stressed every 10 s
        self._mood_start = time.time()

        if not demo:
            self._connect_serial(port, baud)

    # ── Serial ────────────────────────────────────────────────

    def _connect_serial(self, port: str, baud: int):
        if not SERIAL_OK:
            self._serial_error = "pyserial not installed"
            self.demo = True
            return
        try:
            with self._serial_lock:
                if self._ser and self._ser.is_open:
                    self._ser.close()
                self._ser = serial.Serial(port, baud, timeout=0.05)
                self.demo = False
                self._serial_error = None
                # Read handshake lines (give the board 1 s to boot)
                time.sleep(0.8)
                self._parse_handshake()
        except Exception as e:
            self._serial_error = str(e)
            self.demo = True

    def _parse_handshake(self):
        """Read startup lines from the board to detect ADC range."""
        if not (self._ser and self._ser.is_open):
            return
        deadline = time.time() + 2.0
        while time.time() < deadline:
            try:
                raw = self._ser.readline().decode("ascii", errors="ignore").strip()
                if raw.startswith("ADC_MAX:"):
                    self.adc_max   = int(raw.split(":")[1])
                    self.board_type = "ESP32" if self.adc_max > 1023 else "AVR"
                elif raw.startswith("FS:"):
                    self.fs = int(raw.split(":")[1])
                elif raw == "WAVEFORM_START":
                    continue
                elif raw and raw.isdigit():
                    # Already into sample stream — handshake complete
                    break
            except Exception:
                break

    def connect(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self._connect_serial(port, baud)

    def disconnect(self):
        with self._serial_lock:
            if self._ser and self._ser.is_open:
                self._ser.close()
        self._ser  = None
        self.demo  = True
        self._serial_error = None

    @property
    def is_connected(self):
        return (not self.demo) and (self._ser is not None) and self._ser.is_open

    @property
    def connection_error(self):
        return self._serial_error

    def _read_serial(self, n: int = 20) -> np.ndarray:
        samples = []
        with self._serial_lock:
            if not (self._ser and self._ser.is_open):
                self.demo = True
                return np.zeros(n)
            for _ in range(n * 2):           # read extra to allow for skips
                if len(samples) >= n:
                    break
                try:
                    raw = self._ser.readline().decode("ascii", errors="ignore").strip()
                    if not raw:
                        continue
                    if raw.startswith("RATE:"):
                        # Accuracy diagnostic from board
                        self.reported_rate  = int(raw.split(":")[1])
                        self.sample_rate_ok = 900 < self.reported_rate < 1100
                        continue
                    if raw.startswith(("WAVEFORM_", "ADC_MAX:", "FS:")):
                        continue          # skip handshake lines if repeated
                    val = float(raw)
                    # Normalise to a common ±100 µV-equivalent range
                    # regardless of board ADC resolution
                    val = (val / self.adc_max) * 1023.0
                    samples.append(val)
                except Exception:
                    samples.append(512.0)   # mid-scale on parse error
        return np.array(samples[:n], dtype=float)

    # ── Demo synthesis ────────────────────────────────────────

    def _mood(self) -> int:
        """0=Relaxed, 1=Focused, 2=Stressed (10 s each)"""
        return int((time.time() - self._mood_start) / 10) % 3

    def _synthesise(self, n: int = 20) -> np.ndarray:
        mood = self._mood()
        out  = []
        for _ in range(n):
            t      = self._t
            delta  = (60 + 10 * random.gauss(0, 1)) * np.sin(2 * np.pi * 2  * t)
            theta  = (30 +  5 * random.gauss(0, 1)) * np.sin(2 * np.pi * 6  * t)
            a_amp  = [50, 30, 20][mood]
            alpha  = (a_amp + 5 * random.gauss(0, 1)) * np.sin(2 * np.pi * 10 * t)
            b_amp  = [15, 40, 70][mood]
            beta   = (b_amp  + 5 * random.gauss(0, 1)) * np.sin(2 * np.pi * 20 * t)
            gamma  = (10 +  3 * random.gauss(0, 1)) * np.sin(2 * np.pi * 38 * t)
            noise  = 8 * random.gauss(0, 1)
            out.append(delta + theta + alpha + beta + gamma + noise)
            self._t += self._dt
        return np.array(out)

    # ── Filtering ─────────────────────────────────────────────

    @staticmethod
    def _bandpass(data, low, high, fs):
        nyq = fs / 2
        b, a = butter(4, [low / nyq, high / nyq], btype="band")
        return lfilter(b, a, data)

    @staticmethod
    def _notch(data, freq, fs):
        b, a = iirnotch(freq / (fs / 2), 30)
        return lfilter(b, a, data)

    @staticmethod
    def _bandpower(data, fs, low, high) -> float:
        vals  = np.abs(fft(data))
        freqs = np.fft.fftfreq(len(data), 1 / fs)
        idx   = (freqs >= low) & (freqs <= high)
        return float(np.sum(vals[idx]))

    # ── Public API ────────────────────────────────────────────

    def tick(self, n: int = 20):
        """Pull n new samples, apply filters, update internal buffer."""
        raw = self._synthesise(n) if self.demo else self._read_serial(n)
        for s in raw:
            self._buf.append(float(s))

        if len(self._buf) == self.buffer_size:
            arr = np.array(self._buf, dtype=float)
            arr = self._bandpass(arr, 0.5, 45, self.fs)
            arr = self._notch(arr, 50, self.fs)
            self._filtered = arr

    def get_waveform(self) -> np.ndarray:
        return self._filtered.copy()

    def get_fft(self):
        if len(self._filtered) == 0:
            return np.array([]), np.array([])
        vals  = np.abs(fft(self._filtered))
        freqs = np.fft.fftfreq(len(self._filtered), 1 / self.fs)
        pos   = freqs > 0
        return freqs[pos], vals[pos]

    def get_bands(self) -> dict:
        if len(self._filtered) < self.buffer_size:
            return {k: 0.0 for k in self.BANDS}
        return {
            name: self._bandpower(self._filtered, self.fs, lo, hi)
            for name, (lo, hi) in self.BANDS.items()
        }

    def get_stress_index(self) -> float:
        b = self.get_bands()
        return b["beta"] / (b["alpha"] + 1e-6)

    def get_brain_state(self):
        s = self.get_stress_index()
        if s < 1.2:   return "Relaxed",  "😌", "#10b981"
        elif s < 2.5: return "Focused",  "🧠", "#06b6d4"
        elif s < 4.0: return "Alert",    "⚡", "#f59e0b"
        else:         return "Stressed", "😰", "#ef4444"

    def get_diagnostics(self) -> dict:
        """Returns data quality / accuracy info for the dashboard."""
        return {
            "board":      self.board_type if self.is_connected else "Demo",
            "adc_bits":   12 if self.adc_max > 1023 else 10,
            "adc_max":    self.adc_max,
            "rate_ms":    self.reported_rate,
            "rate_ok":    self.sample_rate_ok,
            "source":     "Live" if self.is_connected else "Demo",
        }
