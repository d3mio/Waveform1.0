"""
app.py – WaveForm Brain-Wave Dashboard  (entry point)
Run with:  streamlit run app.py
"""

import os, time
import streamlit as st
import pandas as pd

# ─── Page config (MUST be first Streamlit call) ───────────────
st.set_page_config(
    page_title="WaveForm · Brain Monitor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────
_CSS = os.path.join(os.path.dirname(__file__), "dashboard", "style.css")
with open(_CSS) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Cached singletons (survive Streamlit hot-reloads) ────────
@st.cache_resource
def _get_engine():
    from dashboard.signal_engine import SignalEngine
    return SignalEngine(fs=200, buffer_size=400, demo=True)

@st.cache_resource
def _get_ml():
    from dashboard.ml_engine import MLEngine
    return MLEngine()

# ─── DB init (once) ───────────────────────────────────────────
@st.cache_resource
def _init_db():
    from dashboard import database as _db
    _db.init_db()
    return _db

db = _init_db()
engine = _get_engine()
ml_engine = _get_ml()

# ─── Session state defaults ───────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(
        columns=["time", "delta", "theta", "alpha", "beta", "gamma", "stress"])
if "running" not in st.session_state:
    st.session_state.running = True
if "session_log" not in st.session_state:
    st.session_state.session_log = []
if "start_ts" not in st.session_state:
    st.session_state.start_ts = time.time()
if "session_id" not in st.session_state:
    st.session_state.session_id = db.create_session(label="Demo")
if "ml_result" not in st.session_state:
    st.session_state.ml_result = {}
if "_tick" not in st.session_state:
    st.session_state._tick = 0
if "page" not in st.session_state:
    st.session_state.page = "📊 Live Monitor"

# ─── Imports ──────────────────────────────────────────────────
from dashboard.components import (
    render_header, render_sidebar,
    render_metric_cards, render_eeg_waveform,
    render_fft_spectrum, render_band_bars,
    render_stress_gauge, render_brain_state_panel,
    render_history_chart, render_session_log,
    render_ml_panel, render_database_panel,
    render_analytics_panel, render_arduino_setup_panel,
)

# ─── Sidebar ──────────────────────────────────────────────────
render_sidebar()

# ─── Tick (acquire data + run ML) ────────────────────────────
if st.session_state.running:
    engine.tick()
    bands  = engine.get_bands()
    stress = engine.get_stress_index()
    state, emoji, color = engine.get_brain_state()
    elapsed = time.time() - st.session_state.start_ts

    ml = ml_engine.predict(bands)
    st.session_state.ml_result = ml

    # Append in-memory history (keep last 300)
    new_row = {"time": elapsed, "stress": stress, **bands}
    st.session_state.history = pd.concat(
        [st.session_state.history, pd.DataFrame([new_row])],
        ignore_index=True,
    ).tail(300)

    # Every 20 ticks: log + persist to DB
    st.session_state._tick += 1
    if st.session_state._tick % 20 == 0:
        st.session_state.session_log.append({
            "time":  time.strftime("%H:%M:%S"),
            "state": f"{emoji} {state}",
            "stress": round(stress, 2),
            "alpha":  round(bands.get("alpha", 0), 1),
            "beta":   round(bands.get("beta",  0), 1),
        })
        db.insert_snapshot(
            st.session_state.session_id,
            elapsed, bands, stress, ml,
        )
else:
    bands  = {k: 0.0 for k in ["delta", "theta", "alpha", "beta", "gamma"]}
    stress = 0.0
    state, emoji, color = "Paused", "⏸", "#888888"
    ml = st.session_state.ml_result

# ─── Header ───────────────────────────────────────────────────
render_header()

page = st.session_state.get("page", "📊 Live Monitor")

# ════════════════════════════════════════════════════
#  PAGE: Live Monitor
# ════════════════════════════════════════════════════
if page == "📊 Live Monitor":
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
elif page == "🤖 ML Analysis":
    render_metric_cards(bands, stress, state, emoji, color)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    render_ml_panel(ml)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1: render_eeg_waveform(engine)
    with c2: render_brain_state_panel(state, emoji, color, stress)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    render_history_chart(st.session_state.history)
    with st.expander("ℹ️ Model Information"):
        st.markdown("""
| Classifier | Algorithm | Labels |
|---|---|---|
| **Stress** | Random Forest (120 trees) | Low · Moderate · High |
| **Depression** | Gradient Boosting (100 est.) | Minimal · Mild · Moderate · Severe |
| **Emotion** | Random Forest (120 trees) | Calm · Happy · Anxious · Sad · Focused · Fatigued |

Features: Delta, Theta, Alpha, Beta, Gamma + 5 derived ratios (θ/α, β/α, α-total, δ/β, asymmetry).  
Models saved to `models/` on first run and reloaded automatically.
        """)

# ════════════════════════════════════════════════════
#  PAGE: Database
# ════════════════════════════════════════════════════
elif page == "🗄️ Database":
    render_database_panel()
    st.markdown("---")
    st.markdown("#### ✏️ Add Annotation")
    a1, a2, a3 = st.columns([1, 2, 1])
    with a1:
        ann_label = st.selectbox("Label", ["Baseline", "Task", "Relaxation", "Custom"])
    with a2:
        ann_note = st.text_input("Note", placeholder="Describe activity…")
    with a3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("💾 Save"):
            db.add_annotation(st.session_state.session_id, ann_label, ann_note)
            st.success("Saved!")

# ════════════════════════════════════════════════════
#  PAGE: Analytics
# ════════════════════════════════════════════════════
elif page == "📈 Analytics":
    render_analytics_panel()

# ════════════════════════════════════════════════════
#  PAGE: Arduino Setup
# ════════════════════════════════════════════════════
elif page == "🔧 Arduino Setup":
    render_arduino_setup_panel()

# ─── Auto-refresh ─────────────────────────────────────────────
if st.session_state.running:
    time.sleep(0.08)
    st.rerun()
