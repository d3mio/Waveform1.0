"""
components.py – WaveForm Dashboard UI
Medical Minimal Design · White theme · Blue accents
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

# ─────────────────────────────────────────────────────────────────────
# PLOT THEME  (light, clinical)
# ─────────────────────────────────────────────────────────────────────

PLOT_BG    = "#ffffff"
PAPER_BG   = "#ffffff"
GRID_COLOR = "#f1f5f9"
FONT_COLOR = "#475569"
TICK_COLOR = "#94a3b8"
PRIMARY    = "#2563eb"

BAND_COLORS = {
    "delta": "#6366f1",
    "theta": "#0891b2",
    "alpha": "#059669",
    "beta":  "#d97706",
    "gamma": "#dc2626",
}

BAND_FILLS = {
    "delta": "rgba(99,102,241,0.12)",
    "theta": "rgba(8,145,178,0.12)",
    "alpha": "rgba(5,150,105,0.12)",
    "beta":  "rgba(217,119,6,0.12)",
    "gamma": "rgba(220,38,38,0.12)",
}


def _base_layout(**kwargs) -> dict:
    return dict(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif", size=12),
        margin=dict(l=8, r=8, t=30, b=8),
        xaxis=dict(
            showgrid=False, zeroline=False,
            color=TICK_COLOR, tickfont=dict(size=10),
            linecolor="#e2e8f0", linewidth=1,
        ),
        yaxis=dict(
            showgrid=True, gridcolor=GRID_COLOR,
            zeroline=False,
            color=TICK_COLOR, tickfont=dict(size=10),
            linecolor="#e2e8f0", linewidth=1,
        ),
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────

def render_header():
    now = time.strftime("%H:%M:%S")
    engine = st.session_state.get("engine")
    connected = engine and engine.is_connected
    running   = st.session_state.get("running", False)

    if connected and running:
        dot_html = '<span class="live-dot"></span>'
        status   = "Monitoring"
        status_c = "#16a34a"
    else:
        dot_html = '<span class="standby-dot"></span>'
        status   = "Standby"
        status_c = "#94a3b8"

    st.markdown(f"""
    <div class="wf-header">
      <div>
        <div class="wf-title">WaveForm EEG Monitor</div>
        <div class="wf-subtitle">ADS1115 · ESP32 · AD8232 · 200 Hz · 16-bit</div>
      </div>
      <div style="text-align:right">
        <div style="display:flex;align-items:center;gap:6px;justify-content:flex-end">
          {dot_html}
          <span style="font-weight:600;font-size:13px;color:{status_c}">{status}</span>
        </div>
        <div style="font-size:11px;color:#94a3b8;margin-top:3px">{now}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# SIDEBAR  (port-only, no demo)
# ─────────────────────────────────────────────────────────────────────

def render_sidebar():
    from dashboard.signal_engine import list_serial_ports

    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="sidebar-logo">
          <div style="font-size:15px;font-weight:700;color:#0f172a;letter-spacing:-0.01em">
            WaveForm
          </div>
          <div style="font-size:11px;color:#94a3b8;margin-top:1px">EEG Monitor</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Device Connection ─────────────────────────────────────
        st.markdown(
            '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
            'text-transform:uppercase;color:#94a3b8;padding:4px 0 8px">Device</div>',
            unsafe_allow_html=True,
        )

        engine = st.session_state.get("engine")
        ports  = list_serial_ports()
        port_options = [p["port"] for p in ports]
        port_labels  = [
            f"{'★ ' if p['is_arduino'] else ''}{p['port']}  {p['description'][:28]}"
            for p in ports
        ]

        c1, c2 = st.columns([4, 1])
        with c1:
            if port_options:
                sel_idx = st.selectbox(
                    "Port", range(len(port_options)),
                    format_func=lambda i: port_labels[i],
                    label_visibility="collapsed",
                )
                selected_port = port_options[sel_idx]
            else:
                st.markdown(
                    '<div style="font-size:12px;color:#94a3b8;padding:8px 0">'
                    'No devices found</div>',
                    unsafe_allow_html=True,
                )
                selected_port = None
        with c2:
            if st.button("↺", help="Refresh port list"):
                st.rerun()

        # Connection status + action button
        if engine and engine.is_connected:
            st.markdown(
                f'<div class="conn-badge connected" style="width:100%;'
                f'justify-content:center;margin:6px 0">● Connected · {engine.port}</div>',
                unsafe_allow_html=True,
            )
            if st.button("Disconnect", use_container_width=True):
                engine.disconnect()
                st.session_state.running = False
                st.rerun()
        else:
            if engine and engine.connection_error:
                st.markdown(
                    f'<div class="conn-badge error" style="width:100%;'
                    f'justify-content:center;margin:6px 0">'
                    f'✕ {engine.connection_error[:40]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="conn-badge disconnected" style="width:100%;'
                    'justify-content:center;margin:6px 0">○ Not connected</div>',
                    unsafe_allow_html=True,
                )

            if selected_port and st.button("Connect", use_container_width=True, type="primary"):
                engine.connect(selected_port, 115200)
                if engine.is_connected:
                    st.session_state.running = True
                st.rerun()

        st.markdown('<hr style="border-color:#e2e8f0;margin:14px 0">', unsafe_allow_html=True)

        # ── Navigation ────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
            'text-transform:uppercase;color:#94a3b8;padding:0 0 8px">Navigation</div>',
            unsafe_allow_html=True,
        )

        current_page = st.session_state.get("page", "Live Monitor")
        pages = [
            ("Live Monitor",   "Monitor"),
            ("ML Analysis",    "Analysis"),
            ("Database",       "Database"),
            ("Analytics",      "Analytics"),
            ("Device Setup",   "Setup"),
        ]
        for page_key, page_label in pages:
            is_active = current_page == page_key
            style = (
                "background:#eff6ff;color:#2563eb;font-weight:600"
                if is_active else "color:#475569"
            )
            if st.button(
                page_label,
                use_container_width=True,
                key=f"nav_{page_key}",
            ):
                st.session_state.page = page_key
                st.rerun()

        st.markdown('<hr style="border-color:#e2e8f0;margin:14px 0">', unsafe_allow_html=True)

        # ── Session stats ─────────────────────────────────────────
        hist    = st.session_state.get("history", pd.DataFrame())
        samples = len(hist)
        src     = "Device" if (engine and engine.is_connected) else "Standby"
        st.markdown(f"""
        <div style="font-size:10px;font-weight:600;letter-spacing:0.08em;
                    text-transform:uppercase;color:#94a3b8;margin-bottom:8px">Session</div>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-size:10px;color:#94a3b8">Samples</div>
            <div style="font-weight:700;font-size:16px;color:#0f172a">{samples}</div>
          </div>
          <div>
            <div style="font-size:10px;color:#94a3b8">Source</div>
            <div style="font-weight:600;font-size:12px;color:#475569">{src}</div>
          </div>
          <div>
            <div style="font-size:10px;color:#94a3b8">Rate</div>
            <div style="font-weight:700;font-size:16px;color:#0f172a">200 Hz</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Reset Session", use_container_width=True, key="reset_session"):
            st.session_state.history = pd.DataFrame(
                columns=["time", "delta", "theta", "alpha", "beta", "gamma", "stress"]
            )
            st.session_state.session_log = []
            st.session_state.start_ts = time.time()
            st.rerun()

        st.markdown("""
        <div style="text-align:center;padding:16px 0 0;font-size:10px;color:#cbd5e1">
          WaveForm v1.0 · ICECAP-Lite
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# STANDBY PLACEHOLDER
# ─────────────────────────────────────────────────────────────────────

def render_standby():
    st.markdown("""
    <div class="standby-screen">
      <div class="standby-icon">⬡</div>
      <div class="standby-title">Waiting for device</div>
      <div class="standby-sub">
        Connect your ESP32 from the sidebar to begin monitoring
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Show a flat line as placeholder EEG
    t = np.linspace(0, 2, 400)
    noise = np.random.normal(0, 0.5, 400)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t, y=noise,
        mode="lines",
        line=dict(color="#e2e8f0", width=1.5),
        showlegend=False,
    ))
    fig.update_layout(
        **_base_layout(height=120),
        title=dict(text="EEG  –  No signal", font=dict(size=12, color="#cbd5e1"), x=0),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# METRIC CARDS
# ─────────────────────────────────────────────────────────────────────

def render_metric_cards(bands: dict, stress: float, state: str,
                        emoji: str, color: str):
    cols = st.columns(6)
    items = [
        ("Delta",        bands.get("delta", 0), BAND_COLORS["delta"], "0.5–4 Hz"),
        ("Theta",        bands.get("theta", 0), BAND_COLORS["theta"], "4–8 Hz"),
        ("Alpha",        bands.get("alpha", 0), BAND_COLORS["alpha"], "8–12 Hz"),
        ("Beta",         bands.get("beta",  0), BAND_COLORS["beta"],  "13–30 Hz"),
        ("Gamma",        bands.get("gamma", 0), BAND_COLORS["gamma"], "30–45 Hz"),
        ("Stress Index", stress,                color,                state),
    ]
    for col, (label, val, clr, sub) in zip(cols, items):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="label">{label}</div>
              <div class="value" style="color:{clr}">{val:.1f}</div>
              <div class="sub">{sub}</div>
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
        line=dict(color=PRIMARY, width=1.2),
        name="EEG",
        showlegend=False,
    ))

    # Envelope
    window = 20
    if len(wf) > window:
        env = pd.Series(wf).rolling(window, center=True).std().fillna(0)
        fig.add_trace(go.Scatter(
            x=t_axis, y=env * 2, mode="lines",
            line=dict(color="#94a3b8", width=1, dash="dot"),
            name="Envelope", opacity=0.6,
        ))

    layout = _base_layout(height=160)
    layout["title"] = dict(
        text="Raw EEG Signal", font=dict(size=11, color=TICK_COLOR), x=0
    )
    layout["legend"] = dict(orientation="h", x=1, xanchor="right", y=1,
                             font=dict(size=10))
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="Time (s)", title_font=dict(size=10))
    fig.update_yaxes(title_text="Amplitude", title_font=dict(size=10))

    st.markdown('<div class="section-title">EEG Waveform</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# FFT SPECTRUM
# ─────────────────────────────────────────────────────────────────────

def render_fft_spectrum(engine):
    freqs, fft_vals = engine.get_fft()
    if len(freqs) == 0:
        return

    mask = freqs <= 60
    fig  = go.Figure()

    band_ranges = [
        ("δ Delta", 0.5, 4,  BAND_COLORS["delta"], BAND_FILLS["delta"]),
        ("θ Theta", 4,   8,  BAND_COLORS["theta"], BAND_FILLS["theta"]),
        ("α Alpha", 8,   12, BAND_COLORS["alpha"], BAND_FILLS["alpha"]),
        ("β Beta",  13,  30, BAND_COLORS["beta"],  BAND_FILLS["beta"]),
        ("γ Gamma", 30,  45, BAND_COLORS["gamma"], BAND_FILLS["gamma"]),
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

    layout = _base_layout(height=200)
    layout["title"] = dict(text="Frequency Spectrum", font=dict(size=11, color=TICK_COLOR), x=0)
    layout["legend"] = dict(orientation="h", x=0, y=1.15, font=dict(size=10))
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="Frequency (Hz)", range=[0, 60], title_font=dict(size=10))
    fig.update_yaxes(title_text="Power", title_font=dict(size=10))

    st.markdown('<div class="section-title">Frequency Spectrum (FFT)</div>', unsafe_allow_html=True)
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
        textfont=dict(size=10, color=TICK_COLOR),
    ))
    layout = _base_layout(height=200)
    layout["title"] = dict(text="Band Powers", font=dict(size=11, color=TICK_COLOR), x=0)
    fig.update_layout(**layout, bargap=0.35)

    st.markdown('<div class="section-title">Band Powers</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# STRESS GAUGE
# ─────────────────────────────────────────────────────────────────────

def render_stress_gauge(stress: float):
    capped = min(stress, 8.0)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=capped,
        number=dict(suffix=" SI", font=dict(size=20, color="#0f172a")),
        gauge=dict(
            axis=dict(range=[0, 8], tickcolor=TICK_COLOR,
                      tickfont=dict(color=TICK_COLOR, size=9)),
            bar=dict(color=PRIMARY),
            bgcolor="#f8fafc",
            bordercolor="#e2e8f0",
            borderwidth=1,
            steps=[
                dict(range=[0, 1.2], color="#dcfce7"),
                dict(range=[1.2, 2.5], color="#dbeafe"),
                dict(range=[2.5, 4.0], color="#fef3c7"),
                dict(range=[4.0, 8.0], color="#fee2e2"),
            ],
            threshold=dict(
                line=dict(color="#dc2626", width=2),
                thickness=0.75, value=4.0,
            ),
        ),
        domain=dict(x=[0, 1], y=[0, 1]),
    ))
    layout = _base_layout(height=200)
    layout["title"] = dict(text="Stress Index", font=dict(size=11, color=TICK_COLOR), x=0)
    fig.update_layout(**layout)

    st.markdown('<div class="section-title">Stress Index</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# HISTORY CHART
# ─────────────────────────────────────────────────────────────────────

def render_history_chart(history: pd.DataFrame):
    st.markdown('<div class="section-title">Band History</div>', unsafe_allow_html=True)
    if history.empty:
        st.markdown(
            '<div style="color:#94a3b8;font-size:12px;padding:10px 0">'
            'No data yet.</div>', unsafe_allow_html=True,
        )
        return

    fig = go.Figure()
    for band, clr in BAND_COLORS.items():
        if band in history.columns:
            fig.add_trace(go.Scatter(
                x=history["time"], y=history[band],
                mode="lines", name=band.capitalize(),
                line=dict(color=clr, width=1.4),
            ))

    layout = _base_layout(height=220)
    layout["legend"] = dict(orientation="h", x=0, y=1.1, font=dict(size=10))
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="Elapsed (s)", title_font=dict(size=10))
    fig.update_yaxes(title_text="Power", title_font=dict(size=10))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# BRAIN STATE
# ─────────────────────────────────────────────────────────────────────

def render_brain_state_panel(state: str, emoji: str, color: str, stress: float):
    level_pct = min(int(stress / 8 * 100), 100)
    st.markdown(f"""
    <div class="wf-card" style="text-align:center;padding:24px 16px">
      <div style="font-size:40px;margin-bottom:10px">{emoji}</div>
      <div style="font-size:18px;font-weight:700;color:{color}">{state}</div>
      <div style="font-size:11px;color:#94a3b8;margin:6px 0 14px">
        Stress Index: <b style="color:{color}">{stress:.2f}</b>
      </div>
      <div class="wf-progress">
        <div class="wf-progress-fill" style="width:{level_pct}%;background:{color}"></div>
      </div>
      <div style="display:flex;justify-content:space-between;
                  font-size:10px;color:#94a3b8;margin-top:4px">
        <span>Relaxed</span><span>Stressed</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# SESSION LOG
# ─────────────────────────────────────────────────────────────────────

def render_session_log(log: list):
    st.markdown('<div class="section-title">Session Log</div>', unsafe_allow_html=True)
    rows_html = ""
    for entry in reversed(log[-10:]):
        rows_html += f"""
        <div class="log-row">
          <span class="log-time">{entry['time']}</span>
          <span class="log-state">{entry['state']}</span>
          <span style="margin-left:auto;font-size:11px;color:#94a3b8">
            SI:{entry['stress']} α:{entry.get('alpha','-')}
          </span>
        </div>"""
    if not rows_html:
        rows_html = '<div style="color:#94a3b8;font-size:12px;padding:6px 0">No entries yet.</div>'
    st.markdown(f'<div class="wf-card" style="padding:12px 14px">{rows_html}</div>',
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# ML PANEL
# ─────────────────────────────────────────────────────────────────────

def render_ml_panel(ml: dict):
    st.markdown('<div class="section-title">ML Inference</div>', unsafe_allow_html=True)
    if not ml:
        return

    def _bar(pct, color):
        return (f'<div class="wf-progress">'
                f'<div class="wf-progress-fill" style="width:{int(pct*100)}%;'
                f'background:{color}"></div></div>')

    sc   = ml.get("stress_confidence", 0)
    ss   = ml.get("stress_label", "—")
    sclr = ml.get("stress_color", PRIMARY)
    dc   = ml.get("depression_confidence", 0)
    ds   = ml.get("depression_label", "—")
    dclr = ml.get("depression_color", "#0891b2")
    ec   = ml.get("emotion_confidence", 0)
    es   = ml.get("emotion_label", "—")
    eclr = ml.get("emotion_color", "#059669")

    col1, col2, col3 = st.columns(3)
    for col, label, val, clr, conf in [
        (col1, "Stress Level",    ss, sclr, sc),
        (col2, "Depression",      ds, dclr, dc),
        (col3, "Emotion State",   es, eclr, ec),
    ]:
        with col:
            st.markdown(f"""
            <div class="ml-card">
              <div class="ml-label">{label}</div>
              <div class="ml-value" style="color:{clr}">{val}</div>
              <div class="ml-conf">Confidence: {conf*100:.0f}%</div>
              {_bar(conf, clr)}
            </div>""", unsafe_allow_html=True)

    # Stress probability chart
    _render_proba_chart(
        ml.get("stress_proba", []),
        ["Low", "Moderate", "High"],
        ["#16a34a", "#d97706", "#dc2626"],
        "Stress Probability",
    )


def _render_proba_chart(probas, labels, colors, title):
    if not probas or len(probas) != len(labels):
        return
    fig = go.Figure(go.Bar(
        x=labels, y=[p * 100 for p in probas],
        marker_color=colors,
        text=[f"{p*100:.1f}%" for p in probas],
        textposition="outside",
        textfont=dict(size=11, color=FONT_COLOR),
    ))
    layout = _base_layout(height=180)
    layout["title"] = dict(text=title, font=dict(size=11, color=TICK_COLOR), x=0)
    fig.update_layout(**layout)
    fig.update_yaxes(range=[0, 115], showgrid=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# DATABASE PANEL
# ─────────────────────────────────────────────────────────────────────

def render_database_panel():
    from dashboard.database import list_sessions, load_snapshots, export_session_csv
    st.markdown('<div class="section-title">Database</div>', unsafe_allow_html=True)

    sessions_df = list_sessions()
    if sessions_df.empty:
        st.info("No sessions recorded yet. Connect a device and start monitoring.")
        return

    st.dataframe(sessions_df, use_container_width=True)

    selected = st.selectbox(
        "Inspect session",
        sessions_df["id"].tolist(),
        format_func=lambda x: f"Session {x} – {sessions_df[sessions_df.id==x]['label'].values[0]}",
    )

    if selected:
        snaps = load_snapshots(selected)
        if not snaps.empty:
            st.markdown(f"**{len(snaps)} snapshots** · Session {selected}")
            st.dataframe(snaps.tail(50), use_container_width=True)

            if st.button("Export to CSV"):
                path = export_session_csv(selected)
                st.success(f"Saved → `{path}`")

            fig = go.Figure()
            for band, clr in BAND_COLORS.items():
                if band in snaps.columns:
                    fig.add_trace(go.Scatter(
                        x=snaps["elapsed_sec"], y=snaps[band],
                        mode="lines", name=band.capitalize(),
                        line=dict(color=clr, width=1.4),
                    ))
            layout = _base_layout(height=220)
            layout["title"] = dict(text="Stored EEG History", font=dict(size=11, color=TICK_COLOR), x=0)
            layout["legend"] = dict(orientation="h", x=0, y=1.1, font=dict(size=10))
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.warning("No snapshots yet for this session.")


# ─────────────────────────────────────────────────────────────────────
# ANALYTICS PANEL
# ─────────────────────────────────────────────────────────────────────

def render_analytics_panel():
    from dashboard.database import load_all_snapshots
    st.markdown('<div class="section-title">Analytics</div>', unsafe_allow_html=True)

    df = load_all_snapshots()
    if df.empty:
        st.info("No data yet. Start monitoring to populate analytics.")
        return

    col1, col2 = st.columns(2)
    with col1:
        if "emotion_label" in df.columns:
            ec = df["emotion_label"].value_counts().reset_index()
            ec.columns = ["emotion", "count"]
            fig = px.pie(ec, values="count", names="emotion",
                         title="Emotion Distribution",
                         color_discrete_sequence=["#2563eb","#0891b2","#059669",
                                                  "#d97706","#dc2626","#7c3aed"])
            layout = _base_layout(height=280)
            layout["title"] = dict(text="Emotion Distribution", font=dict(size=11, color=TICK_COLOR), x=0)
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        if "stress_label" in df.columns:
            sc = df["stress_label"].value_counts().reset_index()
            sc.columns = ["stress", "count"]
            fig = px.bar(sc, x="stress", y="count", title="Stress Distribution",
                         color="stress",
                         color_discrete_map={"Low":"#16a34a","Moderate":"#d97706","High":"#dc2626"})
            layout = _base_layout(height=280)
            layout["title"] = dict(text="Stress Distribution", font=dict(size=11, color=TICK_COLOR), x=0)
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    if "stress_index" in df.columns and "elapsed_sec" in df.columns:
        fig = go.Figure()
        for sess_id in df["session_id"].unique()[-5:]:
            sub = df[df["session_id"] == sess_id]
            fig.add_trace(go.Scatter(
                x=sub["elapsed_sec"], y=sub["stress_index"],
                mode="lines", name=f"Session {sess_id}",
                line=dict(width=1.4),
            ))
        layout = _base_layout(height=240)
        layout["title"] = dict(text="Stress Index Over Time", font=dict(size=11, color=TICK_COLOR), x=0)
        layout["legend"] = dict(orientation="h", x=0, y=1.1, font=dict(size=10))
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────
# DEVICE SETUP PAGE
# ─────────────────────────────────────────────────────────────────────

def render_arduino_setup_panel():
    from dashboard.signal_engine import list_serial_ports
    import os

    st.markdown('<div class="section-title">Device Setup</div>', unsafe_allow_html=True)

    # Wiring
    st.markdown("#### Wiring — ADS1115 + ESP32 + AD8232")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("""
        <div class="wf-card">
          <div style="font-size:12px;font-weight:600;color:#2563eb;margin-bottom:10px">
            Complete Wiring Blueprint
          </div>
          <table style="width:100%;font-size:12px;border-collapse:collapse">
            <tr style="border-bottom:1px solid #f1f5f9">
              <th style="text-align:left;padding:5px;color:#94a3b8;font-weight:500">From</th>
              <th style="text-align:left;padding:5px;color:#94a3b8;font-weight:500">To</th>
              <th style="text-align:left;padding:5px;color:#94a3b8;font-weight:500">Note</th>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#2563eb">ESP32 3V3</td>
              <td style="padding:5px">Red (+) rail</td>
              <td style="padding:5px;color:#94a3b8">Power</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#2563eb">ESP32 GND</td>
              <td style="padding:5px">Blue (–) rail</td>
              <td style="padding:5px;color:#94a3b8">Ground</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#059669">ADS1115 VDD</td>
              <td style="padding:5px">Red (+) rail</td>
              <td style="padding:5px;color:#94a3b8">3.3V</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#059669">ADS1115 GND</td>
              <td style="padding:5px">Blue (–) rail</td>
              <td style="padding:5px;color:#94a3b8">GND</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#059669">ADS1115 ADDR</td>
              <td style="padding:5px">Blue (–) rail</td>
              <td style="padding:5px;color:#94a3b8">I2C addr = 0x48</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#059669">ADS1115 SDA</td>
              <td style="padding:5px">ESP32 GPIO 21</td>
              <td style="padding:5px;color:#94a3b8">I2C data</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#059669">ADS1115 SCL</td>
              <td style="padding:5px">ESP32 GPIO 22</td>
              <td style="padding:5px;color:#94a3b8">I2C clock</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#d97706">ADS1115 A0</td>
              <td style="padding:5px">AD8232 OUTPUT</td>
              <td style="padding:5px;color:#94a3b8">EEG signal</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#d97706">AD8232 VIN</td>
              <td style="padding:5px">Red (+) rail</td>
              <td style="padding:5px;color:#94a3b8">3.3V</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#d97706">AD8232 GND</td>
              <td style="padding:5px">Blue (–) rail</td>
              <td style="padding:5px;color:#94a3b8">GND</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#d97706">AD8232 SDN</td>
              <td style="padding:5px">Red (+) rail</td>
              <td style="padding:5px;color:#94a3b8">Keep ON</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9">
              <td style="padding:5px;color:#d97706">AD8232 LO+</td>
              <td style="padding:5px">ESP32 GPIO 2</td>
              <td style="padding:5px;color:#94a3b8">Lead-off detect</td>
            </tr>
            <tr>
              <td style="padding:5px;color:#d97706">AD8232 LO–</td>
              <td style="padding:5px">ESP32 GPIO 4</td>
              <td style="padding:5px;color:#94a3b8">Lead-off detect</td>
            </tr>
          </table>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="wf-card">
          <div style="font-size:12px;font-weight:600;color:#2563eb;margin-bottom:10px">
            Signal Parameters
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div style="background:#eff6ff;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em">Sample Rate</div>
              <div style="font-size:18px;font-weight:700;color:#2563eb">200 Hz</div>
            </div>
            <div style="background:#f0fdf4;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em">ADC</div>
              <div style="font-size:18px;font-weight:700;color:#16a34a">16-bit</div>
            </div>
            <div style="background:#fefce8;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em">Range</div>
              <div style="font-size:18px;font-weight:700;color:#d97706">±4V</div>
            </div>
            <div style="background:#fff7ed;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em">Baud</div>
              <div style="font-size:18px;font-weight:700;color:#ea580c">115200</div>
            </div>
          </div>
          <div style="margin-top:10px;font-size:11px;color:#94a3b8;line-height:1.6">
            Filter chain:<br>
            Bandpass 0.5–45 Hz<br>
            Notch 50 Hz<br>
            GAIN_ONE (±4.096 V)
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Sketch")
    sketch_path = os.path.join(
        os.path.dirname(__file__), "..", "arduino",
        "waveform_eeg_bridge", "waveform_eeg_bridge.ino"
    )
    if os.path.exists(sketch_path):
        with open(sketch_path) as f:
            sketch = f.read()
        st.code(sketch, language="cpp")
        st.download_button("Download .ino", data=sketch,
                           file_name="waveform_eeg_bridge.ino", mime="text/plain")
    else:
        st.warning("Sketch not found.")

    st.markdown("---")
    st.markdown("#### Detected Devices")
    ports = list_serial_ports()
    if ports:
        for p in ports:
            badge = "ESP32 / Arduino" if p["is_arduino"] else "Serial device"
            bclr  = "#16a34a" if p["is_arduino"] else "#94a3b8"
            st.markdown(f"""
            <div class="wf-card" style="display:flex;align-items:center;gap:14px;
                        padding:12px 16px;margin-bottom:6px">
              <div>
                <div style="font-weight:600;color:#0f172a">{p['port']}</div>
                <div style="font-size:12px;color:#94a3b8">{p['description']}</div>
              </div>
              <div style="margin-left:auto">
                <span class="conn-badge" style="background:#f0fdf4;color:{bclr}">{badge}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="wf-card" style="text-align:center;color:#94a3b8;padding:20px">'
            'No devices found. Connect ESP32 and refresh.</div>',
            unsafe_allow_html=True,
        )
