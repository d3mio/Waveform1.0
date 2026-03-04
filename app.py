"""
app.py – WaveForm Brain-Wave Dashboard
Medical Minimal Design · Standby-first mode
Run: streamlit run app.py
"""

import os, time
import streamlit as st
import pandas as pd

# ─── Page config (must be first) ──────────────────────────────
st.set_page_config(
    page_title="WaveForm · EEG Monitor",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────
_CSS = os.path.join(os.path.dirname(__file__), "dashboard", "style.css")
with open(_CSS) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Cached singletons ────────────────────────────────────────
@st.cache_resource
def _get_engine():
    from dashboard.signal_engine import SignalEngine
    # Always start in standby (demo=False, no port) — connect from sidebar
    return SignalEngine(fs=200, buffer_size=400, demo=True)

@st.cache_resource
def _get_ml():
    from dashboard.ml_engine import MLEngine
    return MLEngine()

@st.cache_resource
def _init_db():
    from dashboard import database as _db
    _db.init_db()
    return _db

db        = _init_db()
engine    = _get_engine()
ml_engine = _get_ml()

# Expose engine in session state for sidebar access
st.session_state.engine = engine

# ─── Session state defaults ───────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(
        columns=["time", "delta", "theta", "alpha", "beta", "gamma", "stress"])
if "running" not in st.session_state:
    st.session_state.running = False     # standby until device connects
if "session_log" not in st.session_state:
    st.session_state.session_log = []
if "start_ts" not in st.session_state:
    st.session_state.start_ts = time.time()
if "session_id" not in st.session_state:
    st.session_state.session_id = db.create_session(label="Live")
if "ml_result" not in st.session_state:
    st.session_state.ml_result = {}
if "_tick" not in st.session_state:
    st.session_state._tick = 0
if "page" not in st.session_state:
    st.session_state.page = "Live Monitor"

# ─── Imports ──────────────────────────────────────────────────
from dashboard.components import (
    render_header, render_sidebar, render_standby,
    render_metric_cards, render_eeg_waveform,
    render_fft_spectrum, render_band_bars,
    render_stress_gauge, render_brain_state_panel,
    render_history_chart, render_session_log,
    render_ml_panel, render_database_panel,
    render_analytics_panel, render_arduino_setup_panel,
)

# ─── Sidebar (always visible) ─────────────────────────────────
render_sidebar()

# ─── Data tick ────────────────────────────────────────────────
connected = engine.is_connected
running   = st.session_state.running and connected

if running:
    engine.tick()
    bands  = engine.get_bands()
    stress = engine.get_stress_index()
    state, emoji, color = engine.get_brain_state()
    elapsed = time.time() - st.session_state.start_ts

    ml = ml_engine.predict(bands)
    st.session_state.ml_result = ml

    new_row = {"time": elapsed, "stress": stress, **bands}
    st.session_state.history = pd.concat(
        [st.session_state.history, pd.DataFrame([new_row])],
        ignore_index=True,
    ).tail(300)

    st.session_state._tick += 1
    if st.session_state._tick % 20 == 0:
        st.session_state.session_log.append({
            "time":  time.strftime("%H:%M:%S"),
            "state": state,
            "stress": round(stress, 2),
            "alpha":  round(bands.get("alpha", 0), 1),
            "beta":   round(bands.get("beta",  0), 1),
        })
        db.insert_snapshot(st.session_state.session_id, elapsed, bands, stress, ml)
else:
    bands  = {k: 0.0 for k in ["delta", "theta", "alpha", "beta", "gamma"]}
    stress = 0.0
    state, emoji, color = "Standby", "—", "#94a3b8"
    ml = st.session_state.ml_result

# ─── Header ───────────────────────────────────────────────────
render_header()

page = st.session_state.get("page", "Live Monitor")

# ════════════════════════════════════════════════════
#  PAGE: Live Monitor
# ════════════════════════════════════════════════════
if page == "Live Monitor":
    if not connected:
        render_standby()
    else:
        render_metric_cards(bands, stress, state, emoji, color)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        render_eeg_waveform(engine)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 1.4, 1])
        with c1: render_fft_spectrum(engine)
        with c2: render_band_bars(bands)
        with c3: render_stress_gauge(stress)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        c4, c5, c6 = st.columns([2.4, 1, 1.2])
        with c4: render_history_chart(st.session_state.history)
        with c5: render_brain_state_panel(state, emoji, color, stress)
        with c6: render_session_log(st.session_state.session_log)

# ════════════════════════════════════════════════════
#  PAGE: ML Analysis
# ════════════════════════════════════════════════════
elif page == "ML Analysis":
    if not connected:
        render_standby()
    else:
        render_metric_cards(bands, stress, state, emoji, color)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        render_ml_panel(ml)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        with c1: render_eeg_waveform(engine)
        with c2: render_brain_state_panel(state, emoji, color, stress)
        render_history_chart(st.session_state.history)
        with st.expander("Model Information"):
            st.markdown("""
| Classifier | Algorithm | Labels |
|---|---|---|
| **Stress** | Random Forest (120 trees) | Low · Moderate · High |
| **Depression** | Gradient Boosting (100 est.) | Minimal · Mild · Moderate · Severe |
| **Emotion** | Random Forest (120 trees) | Calm · Happy · Anxious · Sad · Focused · Fatigued |

Features: Delta, Theta, Alpha, Beta, Gamma + 5 derived ratios.  
Models saved to `models/` on first run and reloaded automatically.
            """)

# ════════════════════════════════════════════════════
#  PAGE: Database
# ════════════════════════════════════════════════════
elif page == "Database":
    render_database_panel()
    st.markdown("---")
    st.markdown("#### Add Annotation")
    a1, a2, a3 = st.columns([1, 2, 1])
    with a1:
        ann_label = st.selectbox("Label", ["Baseline", "Task", "Relaxation", "Custom"])
    with a2:
        ann_note = st.text_input("Note", placeholder="Describe the activity…")
    with a3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Save"):
            db.add_annotation(st.session_state.session_id, ann_label, ann_note)
            st.success("Annotation saved.")

# ════════════════════════════════════════════════════
#  PAGE: Analytics
# ════════════════════════════════════════════════════
elif page == "Analytics":
    render_analytics_panel()

# ════════════════════════════════════════════════════
#  PAGE: Device Setup
# ════════════════════════════════════════════════════
elif page == "Device Setup":
    render_arduino_setup_panel()

# ─── Auto-refresh (only when live) ───────────────────────────
if running:
    time.sleep(0.08)
    st.rerun()
