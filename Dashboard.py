import serial
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, iirnotch
from scipy.fft import fft
import pandas as pd
import time

# ======================
# CONFIG
# ======================
PORT = 'COM3'   # Change to your port
FS = 200
BUFFER_SIZE = 1000

ser = serial.Serial(PORT, 115200)

data_buffer = []
start_time = time.time()

# ======================
# FILTERS
# ======================

def bandpass(data, lowcut, highcut, fs):
    b, a = butter(4, [lowcut/(fs/2), highcut/(fs/2)], btype='band')
    return lfilter(b, a, data)

def notch(data, freq, fs):
    b, a = iirnotch(freq/(fs/2), 30)
    return lfilter(b, a, data)

def bandpower(data, fs, low, high):
    fft_vals = np.abs(fft(data))
    freqs = np.fft.fftfreq(len(data), 1/fs)
    idx = np.logical_and(freqs >= low, freqs <= high)
    return np.sum(fft_vals[idx])

# ======================
# PLOTTING
# ======================

plt.ion()
fig = plt.figure(figsize=(12,8))

ax1 = fig.add_subplot(311)
ax2 = fig.add_subplot(312)
ax3 = fig.add_subplot(313)

csv_data = []

while True:
    try:
        line = ser.readline().decode().strip()
        value = int(line)
        data_buffer.append(value)

        if len(data_buffer) > BUFFER_SIZE:
            data_buffer.pop(0)

        if len(data_buffer) == BUFFER_SIZE:

            filtered = bandpass(data_buffer, 1, 40, FS)
            filtered = notch(filtered, 50, FS)

            # ===== Waveform =====
            ax1.clear()
            ax1.plot(filtered)
            ax1.set_title("Live EEG Waveform")

            # ===== FFT =====
            fft_vals = np.abs(fft(filtered))
            freqs = np.fft.fftfreq(len(filtered), 1/FS)

            ax2.clear()
            ax2.plot(freqs[:500], fft_vals[:500])
            ax2.set_title("Frequency Spectrum")

            # ===== Band Powers =====
            delta = bandpower(filtered, FS, 0.5, 4)
            theta = bandpower(filtered, FS, 4, 8)
            alpha = bandpower(filtered, FS, 8, 12)
            beta  = bandpower(filtered, FS, 13, 30)

            ax3.clear()
            ax3.bar(["Delta","Theta","Alpha","Beta"],
                    [delta,theta,alpha,beta])
            ax3.set_title("Brainwave Bands")

            # ===== Stress Index =====
            stress_index = beta / (alpha + 1)

            if stress_index < 1:
                state = "Relaxed 😌"
            elif stress_index < 2:
                state = "Normal 🙂"
            else:
                state = "Stressed 😰"

            print(f"Stress Index: {stress_index:.2f} | State: {state}")

            # ===== Save CSV =====
            timestamp = time.time() - start_time
            csv_data.append([timestamp, delta, theta, alpha, beta, stress_index])

            if len(csv_data) % 50 == 0:
                df = pd.DataFrame(csv_data,
                                  columns=["Time","Delta","Theta","Alpha","Beta","Stress"])
                df.to_csv("eeg_data.csv", index=False)

            plt.pause(0.01)

    except:
        pass