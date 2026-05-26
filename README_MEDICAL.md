# WaveForm: Medical EEG Analytics System 🔬

Welcome to the new **WaveForm**—a premium, clinical-grade EEG monitoring and analytics application. This version transforms the dashboard into a native desktop experience with cloud-backed data synchronization.

## ✨ New Features

### 1. Medical Crystal Theme
- **clinical Aesthetics**: A clean, high-contrast white theme with blue accents and premium typography (Outfit & Inter).
- **Responsive Branding**: The WaveForm logo is now prominent and styled for a professional medical software feel.
- **Improved Clarity**: All dark/black UI blocks have been replaced with elegant white cards and subtle shadows.

### 2. Multi-band Spectral Waveform
- **Colorful Analytics**: The EEG graph now overlays the five key brainwave bands (Delta, Theta, Alpha, Beta, Gamma) in distinct colors.
- **Precision Hover**: Hover over the graph to see localized µV values for each frequency band in real-time.

### 3. Native Desktop App Mode
- **Zero Browser Lag**: Run WaveForm as a standalone desktop application.
- **Native Window**: Launches in a dedicated OS window (Mac/Windows/Linux) using `pywebview`.
- **Launch**: `python run_desktop.py`

### 4. Cloud DB Integration (Supabase)
- **Global Sync**: Sync your sessions, snapshots, and annotations to a secure cloud database.
- **Seamless Local Fallback**: Continues to store data in the local SQLite database if cloud is offline.

---

## 🚀 Setup & Launch

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Cloud (Optional)
Create a file named `.waveform_env` in the root directory and add your Supabase credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

### 3. Start the Application
- **Desktop Mode (Recommended)**:
  ```bash
  python run_desktop.py
  ```
- **Standard Mode**:
  ```bash
  ./waveform.sh start
  ```

---

## 🛠️ Technical Details
- **Frontend**: Streamlit + Plotly (Custom CSS Injection)
- **Engine**: Scipy Signal Processing (Butterworth/IIR Notch)
- **Storage**: SQLite3 (Local) + Supabase (Cloud)
- **Wrapper**: PyWebView
