"""
components.py – All Streamlit UI render functions for WaveForm Dashboard
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import time


# ─────────────────────────────────────────────────────────────────────
# SHARED PLOT THEME
# ─────────────────────────────────────────────────────────────────────

PLOT_BG    = "rgba(0,0,0,0)"
PAPER_BG   = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(255,255,255,0.05)"
FONT_COLOR = "#a0a8d0"
BAND_COLORS = {
    "delta": "#a855f7",
    "theta": "#06b6d4",
    "alpha": "#10b981",
    "beta":  "#f59e0b",
    "gamma": "#ef4444",
}


def _base_layout(**kwargs) -> dict:
    return dict(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_COLOR, family="Inter"),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False, color=FONT_COLOR),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR,
                   zeroline=False, color=FONT_COLOR),
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────

def render_header():
    now = time.strftime("%H:%M:%S")
    running = st.session_state.get("running", True)
    status_dot = "#10b981" if running else "#ef4444"
    status_txt = "Live" if running else "Paused"
    st.markdown(f"""
    <div class="wf-header">
      <div>
        <div class="wf-title">🧠 WaveForm</div>
        <div class="wf-subtitle">Real-time EEG Brain Wave Monitor &amp; ML Inference Engine</div>
      </div>
      <div style="text-align:right">
        <div style="display:flex;align-items:center;gap:8px;justify-content:flex-end">
          <span class="dot" style="background:{status_dot};width:10px;height:10px;
                border-radius:50%;display:inline-block;
                animation:pulse-dot 1.4s ease-in-out infinite"></span>
          <span style="font-weight:600;font-size:14px;color:{'#10b981' if running else '#ef4444'}">{status_txt}</span>
        </div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px">⏰ {now}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────

def render_sidebar():
    from dashboard.signal_engine import list_serial_ports

    with st.sidebar:
        st.markdown("""
        <div style='text-align:center;padding:20px 0 10px'>
          <div style='font-size:36px'>🧠</div>
          <div style='font-family:Space Grotesk,sans-serif;font-size:20px;
                      font-weight:700;background:linear-gradient(135deg,#a78bfa,#06b6d4);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
            WaveForm
          </div>
          <div style='font-size:11px;color:#6b7280;margin-top:2px'>Neurotechnology Monitor</div>
        </div>
        <hr style='border-color:rgba(120,80,255,0.18);margin:10px 0 20px'>
        """, unsafe_allow_html=True)

        # ── Controls ──
        st.markdown("### ⚙️ Controls")
        if st.session_state.get("running", True):
            if st.button("⏸ Pause Monitoring", use_container_width=True):
                st.session_state.running = False
        else:
            if st.button("▶ Resume Monitoring", use_container_width=True):
                st.session_state.running = True

        if st.button("🔄 Reset Session", use_container_width=True):
            st.session_state.history = pd.DataFrame(
                columns=["time", "delta", "theta", "alpha", "beta", "gamma", "stress"]
            )
            st.session_state.session_log = []
            import time as t
            st.session_state.start_ts = t.time()
            st.rerun()

        st.markdown("<hr style='border-color:rgba(120,80,255,0.18)'>", unsafe_allow_html=True)

        # ── Arduino / Signal Source ──
        st.markdown("### 📡 Signal Source")

        engine = st.session_state.get("engine")

        mode = st.radio(
            "Mode",
            ["🎭 Demo (Simulated)", "🔌 Arduino (Serial)"],
            index=0 if (engine is None or engine.demo) else 1,
            label_visibility="collapsed",
        )

        if "Arduino" in mode:
            # Port scanner
            ports = list_serial_ports()
            port_options = [p["port"] for p in ports]
            port_labels  = [
                f"{'⭐ ' if p['is_arduino'] else ''}{p['port']} – {p['description'][:30]}"
                for p in ports
            ]

            col_r, col_btn = st.columns([3, 1])
            with col_r:
                if port_options:
                    sel_idx = st.selectbox(
                        "Port", range(len(port_options)),
                        format_func=lambda i: port_labels[i],
                        label_visibility="collapsed",
                    )
                    selected_port = port_options[sel_idx]
                else:
                    st.warning("No serial ports found")
                    selected_port = None
            with col_btn:
                if st.button("🔍", help="Refresh port list"):
                    st.rerun()

            baud = st.selectbox(
                "Baud Rate",
                [9600, 19200, 57600, 115200, 250000],
                index=3,
                label_visibility="visible",
            )

            # Connection status
            if engine:
                if engine.is_connected:
                    st.markdown(f"""
                    <div style='background:rgba(16,185,129,0.12);border:1px solid #10b981;
                                border-radius:8px;padding:8px 12px;font-size:12px;margin:6px 0'>
                      🟢 <b>Connected</b> — {engine.port} @ {engine.baud} baud
                    </div>""", unsafe_allow_html=True)
                    if st.button("⛔ Disconnect", use_container_width=True):
                        engine.disconnect()
                        st.rerun()
                else:
                    if engine.connection_error:
                        st.markdown(f"""
                        <div style='background:rgba(239,68,68,0.12);border:1px solid #ef4444;
                                    border-radius:8px;padding:8px 12px;font-size:12px;margin:6px 0'>
                          🔴 <b>Error:</b> {engine.connection_error}
                        </div>""", unsafe_allow_html=True)
                    if selected_port and st.button("🔌 Connect to Arduino", use_container_width=True):
                        engine.connect(selected_port, baud)
                        st.rerun()
        else:
            # Switch back to demo
            if engine and not engine.demo:
                engine.disconnect()

        st.markdown("<hr style='border-color:rgba(120,80,255,0.18)'>", unsafe_allow_html=True)

        # ── Navigation ──
        st.markdown("### 🧭 Navigation")
        page = st.radio(
            "Go to",
            ["📊 Live Monitor", "🤖 ML Analysis", "🗄️ Database", "📈 Analytics", "🔧 Arduino Setup"],
            label_visibility="collapsed",
        )
        st.session_state.page = page

        st.markdown("<hr style='border-color:rgba(120,80,255,0.18)'>", unsafe_allow_html=True)

        # ── Session stats ──
        hist    = st.session_state.get("history", pd.DataFrame())
        samples = len(hist)
        src     = "🔌 Arduino" if (engine and engine.is_connected) else "🎭 Demo"
        st.markdown(f"""
        <div class="wf-card" style="margin-top:6px">
          <div class="section-title">📊 Session Stats</div>
          <div style="display:flex;justify-content:space-between;margin-top:8px">
            <div><div style="font-size:10px;color:#6b7280">Snapshots</div>
                 <div style="font-weight:700;font-size:16px">{samples}</div></div>
            <div><div style="font-size:10px;color:#6b7280">Source</div>
                 <div style="font-weight:700;font-size:13px">{src}</div></div>
            <div><div style="font-size:10px;color:#6b7280">FS</div>
                 <div style="font-weight:700;font-size:16px">200 Hz</div></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align:center;padding:16px 0 0;font-size:10px;color:#374151'>
          WaveForm v1.0 · ICECAP-Lite<br>© 2026 Neurotechnology Lab
        </div>
        """, unsafe_allow_html=True)



# ─────────────────────────────────────────────────────────────────────
# METRIC CARDS
# ─────────────────────────────────────────────────────────────────────

def render_metric_cards(bands: dict, stress: float, state: str,
                        emoji: str, color: str):
    cols = st.columns(6)
    items = [
        ("Delta", bands.get("delta", 0), "#a855f7", "0.5–4 Hz · Deep Sleep"),
        ("Theta", bands.get("theta", 0), "#06b6d4", "4–8 Hz · Drowsy"),
        ("Alpha", bands.get("alpha", 0), "#10b981", "8–12 Hz · Relaxed"),
        ("Beta",  bands.get("beta",  0), "#f59e0b", "13–30 Hz · Active"),
        ("Gamma", bands.get("gamma", 0), "#ef4444", "30–45 Hz · Focus"),
        ("Stress Index", stress,          color,    f"{emoji} {state}"),
    ]
    for col, (label, val, clr, sub) in zip(cols, items):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="label">{label}</div>
              <div class="value" style="color:{clr}">{val:.1f}</div>
              <div style="font-size:10px;color:#6b7280;margin-top:3px">{sub}</div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# EEG WAVEFORM
# ─────────────────────────────────────────────────────────────────────

def render_eeg_waveform(engine):
    wf = engine.get_waveform()
    if len(wf) == 0:
        return

    t_axis = np.linspace(0, len(wf) / engine.fs, len(wf))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_axis, y=wf,
        mode="lines",
        line=dict(color="#7c3aed", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(124,58,237,0.07)",
        name="EEG",
    ))

    # Rolling envelope
    window = 20
    if len(wf) > window:
        env = pd.Series(wf).rolling(window, center=True).std().fillna(0)
        fig.add_trace(go.Scatter(
            x=t_axis, y=env * 2, mode="lines",
            line=dict(color="#06b6d4", width=1, dash="dot"),
            name="Envelope", opacity=0.5,
        ))

    layout = _base_layout(height=160, title="Live EEG Waveform")
    layout["legend"] = dict(orientation="h", x=1, xanchor="right", y=1)
    fig.update_layout(**layout)

    st.markdown('<div class="section-title">🌊 Raw EEG Signal</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# FFT SPECTRUM
# ─────────────────────────────────────────────────────────────────────

def render_fft_spectrum(engine):
    freqs, fft_vals = engine.get_fft()
    if len(freqs) == 0:
        return

    mask = freqs <= 60
    fig = go.Figure()

    # Band-coloured fills  (rgba fill = hex color at 15% opacity)
    band_ranges = [
        ("Delta", 0.5, 4,  "#a855f7", "rgba(168,85,247,0.15)"),
        ("Theta", 4,   8,  "#06b6d4", "rgba(6,182,212,0.15)"),
        ("Alpha", 8,   12, "#10b981", "rgba(16,185,129,0.15)"),
        ("Beta",  13,  30, "#f59e0b", "rgba(245,158,11,0.15)"),
        ("Gamma", 30,  45, "#ef4444", "rgba(239,68,68,0.15)"),
    ]
    for name, lo, hi, clr, fill in band_ranges:
        bm = mask & (freqs >= lo) & (freqs <= hi)
        if bm.any():
            fig.add_trace(go.Scatter(
                x=freqs[bm], y=fft_vals[bm],
                mode="lines", fill="tozeroy",
                line=dict(color=clr, width=1.5),
                fillcolor=fill,
                name=name,
            ))

    layout = _base_layout(height=200, title="Frequency Spectrum (FFT)")
    layout["legend"] = dict(orientation="h", x=0, y=1.15, xanchor="left")
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="Frequency (Hz)", range=[0, 60])
    fig.update_yaxes(title_text="Power")

    st.markdown('<div class="section-title">📡 Frequency Spectrum</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# BAND POWER BARS
# ─────────────────────────────────────────────────────────────────────

def render_band_bars(bands: dict):
    labels = list(bands.keys())
    values = [bands[k] for k in labels]
    colors = [BAND_COLORS[k] for k in labels]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:.0f}" for v in values],
        textposition="outside",
        textfont=dict(size=11, color="#a0a8d0"),
    ))
    fig.update_layout(**_base_layout(height=200, title="Band Powers"),
                      bargap=0.3)
    fig.update_yaxes(showgrid=True)

    st.markdown('<div class="section-title">📶 Band Powers</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# STRESS GAUGE
# ─────────────────────────────────────────────────────────────────────

def render_stress_gauge(stress: float):
    capped = min(stress, 8.0)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=capped,
        number=dict(suffix=" SI", font=dict(size=20, color="#f0f0ff")),
        gauge=dict(
            axis=dict(range=[0, 8], tickcolor="#6b7280",
                      tickfont=dict(color="#6b7280", size=10)),
            bar=dict(color="#7c3aed"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            steps=[
                dict(range=[0, 1.2], color="rgba(16,185,129,0.18)"),
                dict(range=[1.2, 2.5], color="rgba(6,182,212,0.18)"),
                dict(range=[2.5, 4.0], color="rgba(245,158,11,0.18)"),
                dict(range=[4.0, 8.0], color="rgba(239,68,68,0.18)"),
            ],
            threshold=dict(
                line=dict(color="#ef4444", width=3),
                thickness=0.8, value=4.0
            ),
        ),
        domain=dict(x=[0, 1], y=[0, 1]),
    ))
    fig.update_layout(**_base_layout(height=200, title="Stress Index"))

    st.markdown('<div class="section-title">🎯 Stress Index</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# HISTORY LINE CHART
# ─────────────────────────────────────────────────────────────────────

def render_history_chart(history: pd.DataFrame):
    st.markdown('<div class="section-title">📈 Band History (last 300 s)</div>',
                unsafe_allow_html=True)
    if history.empty:
        st.info("No data yet — monitoring will populate this chart.")
        return

    fig = go.Figure()
    for band, clr in BAND_COLORS.items():
        if band in history.columns:
            fig.add_trace(go.Scatter(
                x=history["time"], y=history[band],
                mode="lines", name=band.capitalize(),
                line=dict(color=clr, width=1.6),
            ))

    layout = _base_layout(height=220, title="")
    layout["legend"] = dict(orientation="h", x=0, y=1.1)
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="Elapsed (s)")
    fig.update_yaxes(title_text="Power")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# BRAIN STATE PANEL
# ─────────────────────────────────────────────────────────────────────

def render_brain_state_panel(state: str, emoji: str, color: str, stress: float):
    st.markdown('<div class="section-title">🧩 Brain State</div>', unsafe_allow_html=True)
    level_pct = min(int(stress / 8 * 100), 100)
    bar_color = color

    st.markdown(f"""
    <div class="wf-card" style="text-align:center;padding:22px 16px">
      <div style="font-size:52px;margin-bottom:8px">{emoji}</div>
      <div style="font-size:22px;font-weight:800;color:{color};
                  font-family:'Space Grotesk',sans-serif">{state}</div>
      <div style="font-size:11px;color:#6b7280;margin:6px 0 14px">
        Stress Index: <b style="color:{color}">{stress:.2f}</b>
      </div>
      <div class="wf-progress">
        <div class="wf-progress-fill" style="width:{level_pct}%;background:{bar_color}"></div>
      </div>
      <div style="display:flex;justify-content:space-between;
                  font-size:10px;color:#4b5563;margin-top:4px">
        <span>Relaxed</span><span>Stressed</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# SESSION LOG
# ─────────────────────────────────────────────────────────────────────

def render_session_log(log: list):
    st.markdown('<div class="section-title">📋 Session Log</div>', unsafe_allow_html=True)
    rows_html = ""
    for entry in reversed(log[-10:]):
        rows_html += f"""
        <div class="log-row">
          <span class="log-time">{entry['time']}</span>
          <span class="log-state">{entry['state']}</span>
          <span style="margin-left:auto;font-size:11px;color:#6b7280">
            SI:{entry['stress']} α:{entry.get('alpha','-')}
          </span>
        </div>"""
    st.markdown(f'<div class="wf-card" style="padding:12px 14px">{rows_html}</div>',
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# ML INFERENCE PANEL
# ─────────────────────────────────────────────────────────────────────

def render_ml_panel(ml: dict):
    st.markdown('<div class="section-title">🤖 ML Inference</div>', unsafe_allow_html=True)
    if not ml:
        return

    def _bar(pct, color):
        return f"""<div class="wf-progress">
          <div class="wf-progress-fill" style="width:{int(pct*100)}%;background:{color}"></div>
        </div>"""

    # Stress
    sc = ml.get("stress_confidence", 0)
    ss = ml.get("stress_label", "—")
    sclr = ml.get("stress_color", "#7c3aed")

    # Depression
    dc = ml.get("depression_confidence", 0)
    ds = ml.get("depression_label", "—")
    dclr = ml.get("depression_color", "#06b6d4")

    # Emotion
    ec = ml.get("emotion_confidence", 0)
    es = ml.get("emotion_label", "—")
    eclr = ml.get("emotion_color", "#10b981")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="ml-card">
          <div class="ml-label">Stress Level</div>
          <div class="ml-value" style="color:{sclr}">{ss}</div>
          <div class="ml-conf">Confidence: {sc*100:.0f}%</div>
          {_bar(sc, sclr)}
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="ml-card">
          <div class="ml-label">Depression Score</div>
          <div class="ml-value" style="color:{dclr}">{ds}</div>
          <div class="ml-conf">Confidence: {dc*100:.0f}%</div>
          {_bar(dc, dclr)}
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="ml-card">
          <div class="ml-label">Emotion State</div>
          <div class="ml-value" style="color:{eclr}">{es}</div>
          <div class="ml-conf">Confidence: {ec*100:.0f}%</div>
          {_bar(ec, eclr)}
        </div>""", unsafe_allow_html=True)

    # Probability distribution bars for each classifier
    _render_proba_chart(
        ml.get("stress_proba", []),
        ["Low", "Moderate", "High"],
        ["#10b981", "#f59e0b", "#ef4444"],
        "Stress Probability Distribution",
    )


def _render_proba_chart(probas, labels, colors, title):
    if not probas or len(probas) != len(labels):
        return
    fig = go.Figure(go.Bar(
        x=labels, y=[p * 100 for p in probas],
        marker_color=colors,
        text=[f"{p*100:.1f}%" for p in probas],
        textposition="outside",
    ))
    fig.update_layout(**_base_layout(height=180, title=title))
    fig.update_yaxes(range=[0, 110], showgrid=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# DATABASE PANEL
# ─────────────────────────────────────────────────────────────────────

def render_database_panel():
    from dashboard.database import (
        list_sessions, load_snapshots, load_all_snapshots, export_session_csv
    )
    st.markdown('<div class="section-title">🗄️ Database Browser</div>',
                unsafe_allow_html=True)

    sessions_df = list_sessions()
    if sessions_df.empty:
        st.info("No sessions recorded yet. Start monitoring to collect data.")
        return

    st.markdown("#### Sessions")
    st.dataframe(sessions_df, use_container_width=True)

    selected = st.selectbox(
        "Select session to inspect",
        sessions_df["id"].tolist(),
        format_func=lambda x: f"Session {x} – {sessions_df[sessions_df.id==x]['label'].values[0]}"
    )

    if selected:
        snaps = load_snapshots(selected)
        if not snaps.empty:
            st.markdown(f"#### Snapshots for Session {selected} ({len(snaps)} rows)")
            st.dataframe(snaps.tail(50), use_container_width=True)

            if st.button("📥 Export to CSV"):
                path = export_session_csv(selected)
                st.success(f"Saved → `{path}`")

            # Quick band-power chart from DB
            fig = go.Figure()
            for band, clr in {
                "alpha": "#10b981", "beta": "#f59e0b",
                "theta": "#06b6d4", "delta": "#a855f7"
            }.items():
                if band in snaps.columns:
                    fig.add_trace(go.Scatter(
                        x=snaps["elapsed_sec"], y=snaps[band],
                        mode="lines", name=band, line=dict(color=clr)
                    ))
            fig.update_layout(**_base_layout(height=220, title="Stored EEG History"))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.warning("No snapshots for this session.")


# ─────────────────────────────────────────────────────────────────────
# ANALYTICS PANEL
# ─────────────────────────────────────────────────────────────────────

def render_analytics_panel():
    from dashboard.database import load_all_snapshots
    st.markdown('<div class="section-title">📈 Analytics</div>', unsafe_allow_html=True)

    df = load_all_snapshots()
    if df.empty:
        st.info("No data in the database yet.")
        return

    col1, col2 = st.columns(2)
    with col1:
        # Emotion distribution
        if "emotion_label" in df.columns:
            ec = df["emotion_label"].value_counts().reset_index()
            ec.columns = ["emotion", "count"]
            fig = px.pie(ec, values="count", names="emotion",
                         title="Emotion Distribution",
                         color_discrete_sequence=px.colors.sequential.Purp)
            fig.update_layout(**_base_layout(height=280))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        # Stress label distribution
        if "stress_label" in df.columns:
            sc = df["stress_label"].value_counts().reset_index()
            sc.columns = ["stress", "count"]
            fig = px.bar(sc, x="stress", y="count",
                         title="Stress Level Distribution",
                         color="stress",
                         color_discrete_map={"Low": "#10b981", "Moderate": "#f59e0b", "High": "#ef4444"})
            fig.update_layout(**_base_layout(height=280))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Rolling stress index over time
    if "stress_index" in df.columns and "elapsed_sec" in df.columns:
        fig = go.Figure()
        for sess_id in df["session_id"].unique()[-5:]:
            subset = df[df["session_id"] == sess_id]
            fig.add_trace(go.Scatter(
                x=subset["elapsed_sec"],
                y=subset["stress_index"],
                mode="lines",
                name=f"Session {sess_id}",
            ))
        fig.update_layout(**_base_layout(height=240, title="Stress Index Over Time (all sessions)"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Depression distribution
    if "depression_label" in df.columns:
        dc = df["depression_label"].value_counts().reset_index()
        dc.columns = ["depression", "count"]
        fig = px.bar(dc, x="depression", y="count",
                     title="Depression Score Distribution",
                     color="depression",
                     color_discrete_map={
                         "Minimal": "#10b981", "Mild": "#a3e635",
                         "Moderate": "#f59e0b", "Severe": "#ef4444"
                     })
        fig.update_layout(**_base_layout(height=240))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# ARDUINO SETUP PAGE
# ─────────────────────────────────────────────────────────────────────

def render_arduino_setup_panel():
    from dashboard.signal_engine import list_serial_ports
    import os

    st.markdown('<div class="section-title">🔧 Arduino Setup Guide</div>',
                unsafe_allow_html=True)

    # ── Step 1: Hardware ──
    st.markdown("### Step 1 — Hardware Wiring")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("""
        <div class="wf-card">
          <div style="font-weight:700;margin-bottom:10px;color:#a78bfa">AD8232 EEG Sensor → Arduino</div>
          <table style="width:100%;font-size:13px;border-collapse:collapse">
            <tr style="border-bottom:1px solid rgba(255,255,255,0.07)">
              <th style="text-align:left;padding:6px;color:#6b7280">Sensor Pin</th>
              <th style="text-align:left;padding:6px;color:#6b7280">Arduino Pin</th>
              <th style="text-align:left;padding:6px;color:#6b7280">Notes</th>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05)">
              <td style="padding:6px;color:#06b6d4">OUTPUT</td>
              <td style="padding:6px;color:#10b981">A0</td>
              <td style="padding:6px;color:#6b7280">EEG signal</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05)">
              <td style="padding:6px;color:#06b6d4">LO+</td>
              <td style="padding:6px;color:#10b981">D10</td>
              <td style="padding:6px;color:#6b7280">Lead-off detect</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05)">
              <td style="padding:6px;color:#06b6d4">LO-</td>
              <td style="padding:6px;color:#10b981">D11</td>
              <td style="padding:6px;color:#6b7280">Lead-off detect</td>
            </tr>
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05)">
              <td style="padding:6px;color:#06b6d4">GND</td>
              <td style="padding:6px;color:#10b981">GND</td>
              <td style="padding:6px;color:#6b7280">Common ground</td>
            </tr>
            <tr>
              <td style="padding:6px;color:#06b6d4">3.3V</td>
              <td style="padding:6px;color:#10b981">3.3V</td>
              <td style="padding:6px;color:#6b7280">Power supply</td>
            </tr>
          </table>
          <div style="margin-top:12px;font-size:11px;color:#6b7280">
            ⚡ Electrode placement: RA → right wrist, LA → left wrist, RL → right leg (ground)
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="wf-card">
          <div style="font-weight:700;margin-bottom:10px;color:#a78bfa">Signal Parameters</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div style="background:rgba(124,58,237,0.1);border-radius:8px;padding:10px;text-align:center">
              <div style="font-size:10px;color:#6b7280">SAMPLE RATE</div>
              <div style="font-size:20px;font-weight:700;color:#a78bfa">200 Hz</div>
            </div>
            <div style="background:rgba(6,182,212,0.1);border-radius:8px;padding:10px;text-align:center">
              <div style="font-size:10px;color:#6b7280">BAUD RATE</div>
              <div style="font-size:20px;font-weight:700;color:#06b6d4">115200</div>
            </div>
            <div style="background:rgba(16,185,129,0.1);border-radius:8px;padding:10px;text-align:center">
              <div style="font-size:10px;color:#6b7280">ADC BITS</div>
              <div style="font-size:20px;font-weight:700;color:#10b981">10-bit</div>
            </div>
            <div style="background:rgba(245,158,11,0.1);border-radius:8px;padding:10px;text-align:center">
              <div style="font-size:10px;color:#6b7280">RANGE</div>
              <div style="font-size:20px;font-weight:700;color:#f59e0b">0–1023</div>
            </div>
          </div>
          <div style="margin-top:12px;font-size:11px;color:#6b7280">
            Filter chain: Bandpass (0.5–45 Hz) + Notch (50 Hz)
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Step 2: Sketch ──
    st.markdown("### Step 2 — Flash the Arduino Sketch")
    sketch_path = os.path.join(
        os.path.dirname(__file__), "..", "arduino", "waveform_eeg_bridge.ino"
    )
    if os.path.exists(sketch_path):
        with open(sketch_path) as f:
            sketch = f.read()
        st.code(sketch, language="cpp")
        st.download_button(
            "📥 Download .ino file",
            data=sketch,
            file_name="waveform_eeg_bridge.ino",
            mime="text/plain",
        )
    else:
        st.warning("Sketch file not found at arduino/waveform_eeg_bridge.ino")

    st.markdown("""
    **Flashing instructions:**
    1. Open **Arduino IDE** → File → Open → select `waveform_eeg_bridge.ino`
    2. Select your board under **Tools → Board** (e.g. *Arduino Uno*)
    3. Select the correct **Tools → Port** (same port shown in the sidebar)
    4. Click **Upload** (→ arrow icon)
    5. Open **Serial Monitor** and verify you see integer values scrolling
    6. Close Serial Monitor, then use the **sidebar** to connect WaveForm
    """)

    st.markdown("---")

    # ── Step 3: Live port check ──
    st.markdown("### Step 3 — Detect Connected Devices")
    ports = list_serial_ports()
    if ports:
        for p in ports:
            badge = "⭐ Arduino detected" if p["is_arduino"] else "🔌 Serial device"
            color = "#10b981" if p["is_arduino"] else "#6b7280"
            st.markdown(f"""
            <div class="wf-card" style="margin-bottom:8px;display:flex;
                        align-items:center;gap:14px;padding:12px 16px">
              <div style="font-size:22px">🔌</div>
              <div>
                <div style="font-weight:700;color:{color}">{p['port']}</div>
                <div style="font-size:12px;color:#6b7280">{p['description']}</div>
              </div>
              <div style="margin-left:auto">
                <span style="background:rgba(16,185,129,0.12);color:{color};
                             border-radius:99px;padding:3px 10px;font-size:11px;font-weight:600">
                  {badge}
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="wf-card" style="text-align:center;padding:24px;color:#6b7280">
          No serial devices found.<br>Connect your Arduino and click 🔍 Refresh in the sidebar.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    > **Tip:** Once your Arduino is connected and the sketch is running, go to
    > **Signal Source** in the sidebar → switch to *Arduino (Serial)* → select your port → click **Connect**.
    """)
