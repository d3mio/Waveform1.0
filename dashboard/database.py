"""
database.py – WaveForm SQLite Storage Layer
============================================
Tables
------
  sessions         – one row per monitoring session
  eeg_snapshots    – periodic (1 s) band-power + ML inference rows
  raw_samples      – optional high-rate raw ADC values
  annotations      – user-added labels / notes for a timestamp
"""

import sqlite3
import os
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load Cloud Env
load_dotenv(".waveform_env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("☁️ Cloud database connected (Supabase)")
    except Exception as e:
        print(f"⚠️ Cloud connection failed: {e}")

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(_PROJECT_ROOT, "data", "waveform.db")

def _connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if they don't exist."""
    conn = _connection()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at  TEXT    NOT NULL,
        ended_at    TEXT,
        label       TEXT,
        notes       TEXT,
        fs          INTEGER DEFAULT 200
    );
    CREATE TABLE IF NOT EXISTS eeg_snapshots (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id      INTEGER REFERENCES sessions(id),
        ts              TEXT    NOT NULL,
        elapsed_sec     REAL,
        delta           REAL,
        theta           REAL,
        alpha           REAL,
        beta            REAL,
        gamma           REAL,
        stress_index    REAL,
        stress_label    TEXT,
        stress_conf     REAL,
        depression_label TEXT,
        depression_conf  REAL,
        emotion_label   TEXT,
        emotion_conf    REAL
    );
    CREATE TABLE IF NOT EXISTS annotations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  INTEGER REFERENCES sessions(id),
        ts          TEXT    NOT NULL,
        label       TEXT,
        note        TEXT
    );
    """)
    conn.commit()
    conn.close()

def create_session(label: str = "Demo", notes: str = "", fs: int = 200) -> int:
    ts = datetime.utcnow().isoformat()
    conn = _connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions (started_at, label, notes, fs) VALUES (?,?,?,?)",
        (ts, label, notes, fs),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    
    if _supabase:
        try:
            _supabase.table("sessions").insert({
                "id": sid, "started_at": ts, "label": label, "notes": notes, "fs": fs
            }).execute()
        except: pass
    return sid

def insert_snapshot(session_id: int, elapsed: float, bands: dict, stress_index: float, ml: dict):
    ts = datetime.utcnow().isoformat()
    conn = _connection()
    data = (
        session_id, ts, elapsed,
        bands.get("delta", 0), bands.get("theta", 0), bands.get("alpha", 0),
        bands.get("beta",  0), bands.get("gamma", 0),
        stress_index, ml.get("stress_label", ""), ml.get("stress_confidence", 0),
        ml.get("depression_label", ""), ml.get("depression_confidence", 0),
        ml.get("emotion_label", ""), ml.get("emotion_confidence", 0),
    )
    conn.execute("""
        INSERT INTO eeg_snapshots
            (session_id, ts, elapsed_sec, delta, theta, alpha, beta, gamma,
             stress_index, stress_label, stress_conf, depression_label, depression_conf,
             emotion_label, emotion_conf)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, data)
    conn.commit()
    conn.close()

    if _supabase:
        try:
            _supabase.table("eeg_snapshots").insert({
                "session_id": session_id, "ts": ts, "elapsed_sec": elapsed,
                "delta": bands.get("delta", 0), "theta": bands.get("theta", 0),
                "alpha": bands.get("alpha", 0), "beta": bands.get("beta", 0),
                "gamma": bands.get("gamma", 0), "stress_index": stress_index,
                "stress_label": ml.get("stress_label", ""), "stress_conf": ml.get("stress_confidence", 0)
            }).execute()
        except: pass

def list_sessions() -> pd.DataFrame:
    conn = _connection()
    df = pd.read_sql("SELECT * FROM sessions ORDER BY id DESC", conn)
    conn.close()
    return df

def load_snapshots(session_id: int) -> pd.DataFrame:
    conn = _connection()
    df = pd.read_sql("SELECT * FROM eeg_snapshots WHERE session_id=? ORDER BY elapsed_sec", conn, params=(session_id,))
    conn.close()
    return df

def load_all_snapshots() -> pd.DataFrame:
    conn = _connection()
    df = pd.read_sql("SELECT s.label as session_label, e.* FROM eeg_snapshots e JOIN sessions s ON e.session_id=s.id ORDER BY e.id DESC LIMIT 5000", conn)
    conn.close()
    return df

def add_annotation(session_id: int, label: str, note: str = ""):
    ts = datetime.utcnow().isoformat()
    conn = _connection()
    conn.execute("INSERT INTO annotations (session_id, ts, label, note) VALUES (?,?,?,?)", (session_id, ts, label, note))
    conn.commit()
    conn.close()
    if _supabase:
        try: _supabase.table("annotations").insert({"session_id": session_id, "ts": ts, "label": label, "note": note}).execute()
        except: pass

def export_session_csv(session_id: int) -> str:
    df = load_snapshots(session_id)
    export_dir = os.path.join(os.path.dirname(DB_PATH), "exports")
    os.makedirs(export_dir, exist_ok=True)
    path = os.path.join(export_dir, f"session_{session_id}.csv")
    df.to_csv(path, index=False)
    return path
