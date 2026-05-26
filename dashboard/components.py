"""
components.py – WaveForm Dashboard UI (v2.1 Fix)
Medical Minimal Design · Fixed Plotly Layouts · Robust Bluetooth
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import time

# ─────────────────────────────────────────────────────────────────────
# PLOT THEME
# ─────────────────────────────────────────────────────────────────────
PLOT_BG    = "#ffffff"
PAPER_BG   = "#ffffff"
GRID_COLOR = "#f1f5f9"
FONT_COLOR = "#475569"
TICK_COLOR = "#94a3b8"
PRIMARY    = "#2563eb"

BAND_COLORS = {
    "delta": "#6366f1", "theta": "#0891b2", "alpha": "#059669",
    "beta":  "#d97706", "gamma": "#dc2626",
}

def _base_layout(height=180, show_axes=True) -> dict:
    """Returns a base layout dictionary for Plotly charts."""
    d = dict(
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif", size=12),
        margin=dict(l=8, r=8, t=30, b=8),
        height=height
    )
    if show_axes:
        d["xaxis"] = dict(showgrid=False, zeroline=False, color=TICK_COLOR, tickfont=dict(size=10))
        d["yaxis"] = dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False, color=TICK_COLOR, tickfont=dict(size=10))
    else:
        d["xaxis"] = dict(visible=False)
        d["yaxis"] = dict(visible=False)
    return d

# ─────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────
def render_header():
    now = time.strftime("%H:%M:%S")
    st.markdown(f"""
    <div style="padding: 16px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 24px; display:flex; justify-content:space-between; align-items:center;">
      <div style="display:flex; align-items: baseline; gap: 12px;">
        <div style="font-size:28px; font-weight:800; color:#0f172a; letter-spacing:-0.03em;">WaveForm</div>
        <div style="font-size:11px; font-weight:500; color:#94a3b8; letter-spacing:0.05em">EEG ANALYTICS</div>
      </div>
      <div style="font-size:11px; color:#94a3b8; font-weight:500">{now}</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# STANDBY / CONNECTION SCREEN
# ─────────────────────────────────────────────────────────────────────
def render_standby():
    from dashboard.signal_engine import list_serial_ports
    
    st.markdown("""
    <div style="text-align:center; padding: 40px 0;">
      <div style="font-size:54px; margin-bottom:15px;">⬡</div>
      <div style="font-size:24px; font-weight:800; color:#0f172a; margin-bottom:8px;">Initialize Connection</div>
      <div style="font-size:13px; color:#64748b; margin-bottom:32px;">Pair 'ESP32-M3-Connect' in Bluetooth settings first</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        engine = st.session_state.get("engine")
        
        mode = st.radio(
            "Transport Mode",
            ["🔌 USB Serial", "📡 Bluetooth", "🌐 WiFi"],
            horizontal=True,
            key="main_conn_mode"
        )
        
        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
        
        if "USB" in mode:
            ports = list_serial_ports()
            if not ports:
                st.warning("Connect your device to USB.")
            else:
                port_names = [p["port"] for p in ports]
                labels = [f"{p['port']} ({p['description'][:20]})" for p in ports]
                sid = st.selectbox("USB Port", range(len(labels)), format_func=lambda i: labels[i])
                if st.button("CONNECT USB", use_container_width=True, type="primary"):
                    engine.connect(port_names[sid], 115200)
                    st.session_state.running = True
                    st.rerun()

        elif "Bluetooth" in mode:
            # On macOS, we auto-detect the bridge
            st.info("Searching for macOS Bluetooth Serial Bridge...")
            if st.button("CONNECT BLUETOOTH", use_container_width=True, type="primary"):
                with st.spinner("Linking to ESP32-M3-Connect..."):
                    engine.connect_bluetooth() # Smart auto-detect in v2.1
                if engine.is_connected:
                    st.session_state.running = True
                    st.rerun()
                else:
                    st.error("Bridge not found. Is it paired in Mac Bluetooth settings?")

        elif "WiFi" in mode:
            ip = st.text_input("Wireless IP", placeholder="192.168.x.x")
            if ip and st.button("CONNECT WIFI", use_container_width=True, type="primary"):
                with st.spinner("Connecting..."):
                    engine.connect_wifi(ip, 5005)
                if engine.is_connected:
                    st.session_state.running = True
                st.rerun()

    st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
    
    # Placeholder line
    t = np.linspace(0, 2, 400)
    noise = np.random.normal(0, 0.1, 400)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=noise, mode="lines", line=dict(color="#f1f5f9", width=1), showlegend=False))
    fig.update_layout(**_base_layout(height=100, show_axes=False))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.write("### Dashboard")
        if st.session_state.get("engine") and st.session_state.engine.is_connected:
            if st.button("DISCONNECT"):
                st.session_state.engine.disconnect()
                st.session_state.running = False
                st.rerun()
        
        st.markdown("---")
        current_page = st.session_state.get("page", "Live Monitor")
        for p in ["Live Monitor", "ML Analysis", "Database", "Device Setup"]:
            if st.button(p, use_container_width=True, type="primary" if current_page == p else "secondary"):
                st.session_state.page = p
                st.rerun()

# ─────────────────────────────────────────────────────────────────────
# DASHBOARD COMPONENTS
# ─────────────────────────────────────────────────────────────────────

def render_metric_cards(bands: dict, stress: float, state: str, emoji: str, color: str):
    cols = st.columns(6)
    items = [
        ("Delta", bands.get("delta", 0), BAND_COLORS["delta"]),
        ("Theta", bands.get("theta", 0), BAND_COLORS["theta"]),
        ("Alpha", bands.get("alpha", 0), BAND_COLORS["alpha"]),
        ("Beta",  bands.get("beta",  0), BAND_COLORS["beta"]),
        ("Gamma", bands.get("gamma", 0), BAND_COLORS["gamma"]),
        ("Stress", stress,               color),
    ]
    for col, (label, val, clr) in zip(cols, items):
        with col:
            st.markdown(f"""
            <div style="background:white; border:1px solid #e2e8f0; border-radius:12px; padding:12px; box-shadow:0 1px 3px rgba(0,0,0,0.02)">
              <div style="font-size:9px; font-weight:700; color:#94a3b8; text-transform:uppercase">{label}</div>
              <div style="font-size:22px; font-weight:700; color:{clr}">{val:.1f}</div>
            </div>
            """, unsafe_allow_html=True)

def render_eeg_waveform(engine):
    wf = engine.get_waveform()
    if len(wf) == 0: return
    t_axis = np.linspace(0, len(wf) / engine.fs, len(wf))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_axis, y=wf, mode="lines", line=dict(color="#f1f5f9", width=0.8), showlegend=False))
    
    for b, clr in BAND_COLORS.items():
        bw = engine.get_band_waveform(b)
        if len(bw) == len(t_axis):
            fig.add_trace(go.Scatter(x=t_axis, y=bw, mode="lines", line=dict(color=clr, width=1.5), name=b.capitalize()))

    fig.update_layout(**_base_layout(height=280))
    st.plotly_chart(fig, use_container_width=True)

def render_fft_spectrum(engine):
    freqs, fft_vals = engine.get_fft()
    if len(freqs) == 0: return
    mask = freqs <= 50
    fig = go.Figure(go.Scatter(x=freqs[mask], y=fft_vals[mask], fill='tozeroy', line=dict(color=PRIMARY)))
    fig.update_layout(**_base_layout(height=200))
    st.plotly_chart(fig, use_container_width=True)

def render_band_bars(bands: dict):
    fig = go.Figure(go.Bar(x=list(bands.keys()), y=list(bands.values()), marker_color=[BAND_COLORS[k] for k in bands.keys()]))
    fig.update_layout(**_base_layout(height=200))
    st.plotly_chart(fig, use_container_width=True)

def render_stress_gauge(stress: float):
    fig = go.Figure(go.Indicator(mode="gauge+number", value=min(stress, 8), gauge={'axis': {'range': [0, 8]}}))
    fig.update_layout(**_base_layout(height=180))
    st.plotly_chart(fig, use_container_width=True)

def render_history_chart(history: pd.DataFrame):
    if history.empty: return
    fig = go.Figure()
    for b, clr in BAND_COLORS.items():
        if b in history.columns:
            fig.add_trace(go.Scatter(x=history["time"], y=history[b], mode="lines", name=b, line=dict(color=clr, width=1.2)))
    fig.update_layout(**_base_layout(height=220))
    st.plotly_chart(fig, use_container_width=True)

def render_brain_state_panel(state: str, emoji: str, color: str, stress: float):
    st.markdown(f"""
    <div style="background:white; border:1px solid #e2e8f0; border-radius:12px; padding:20px; text-align:center;">
      <div style="font-size:40px">{emoji}</div>
      <div style="font-size:18px; font-weight:700; color:{color}">{state}</div>
    </div>
    """, unsafe_allow_html=True)

def render_session_log(log: list):
    for entry in reversed(log[-8:]):
        st.markdown(f"<div style='font-size:11px; margin-bottom:4px; opacity:0.7'>{entry['time']} - {entry['state']}</div>", unsafe_allow_html=True)

def render_ml_panel(ml: dict):
    st.json(ml)

def render_database_panel():
    st.info("Sessions saved to local SQLite.")

def render_analytics_panel():
    st.info("View session history in Database tab.")

def render_arduino_setup_panel():
    st.markdown("### ESP32 Bluetooth Setup (MacBook M3)")
    st.markdown("""
    1. **Install Arduino IDE** (Native Silicon version 2.3+).
    2. **ESP32 Boards**: Add `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json` in Settings.
    3. **Upload Code**: Use the code in `arduino/waveform_eeg_bridge/`.
    4. **Pairing**: Go to *System Settings > Bluetooth* and connect to **ESP32-M3-Connect**.
    5. **Dashboard**: Go back to the Live Monitor and click 'CONNECT BLUETOOTH'.
    
    *Note: If upload hangs, hold the BOOT button on your ESP32.*
    """)
