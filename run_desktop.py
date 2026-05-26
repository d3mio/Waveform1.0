#!/usr/bin/env python3
"""
run_desktop.py – Native Desktop Wrapper for WaveForm
===================================================
Launches the WaveForm dashboard in a dedicated OS window instead of a browser tab.
Requires: pip install pywebview streamlit
"""

import webview
import subprocess
import time
import threading
import sys
import os
import socket

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def run_streamlit():
    """Start the Streamlit server."""
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.headless", "true",
        "--server.port", "8501"
    ])

def main():
    print("🚀 Starting WaveForm Desktop App...")
    
    # Start Streamlit in a background thread
    st_thread = threading.Thread(target=run_streamlit, daemon=True)
    st_thread.start()

    # Wait for server to be ready
    print("⏳ Initializing medical engine...")
    retries = 30
    while not is_port_open(8501) and retries > 0:
        time.sleep(1)
        retries -= 1

    if retries == 0:
        print("❌ Error: Streamlit server failed to start.")
        sys.exit(1)

    # Launch native window
    print("✨ Opening dashboard...")
    webview.create_window(
        'WaveForm · Medical EEG Monitor',
        'http://localhost:8501',
        width=1280,
        height=850,
        min_size=(1024, 720),
        text_select=False,
        confirm_close=True
    )
    
    webview.start(gui='cocoa' if sys.platform == 'darwin' else 'qt')

if __name__ == "__main__":
    main()
