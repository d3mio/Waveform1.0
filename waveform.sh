#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  WaveForm Controller  –  waveform.sh
#  Usage:
#    ./waveform.sh start   → upload sketch + launch dashboard
#    ./waveform.sh stop    → kill all WaveForm processes
#
#  Or run interactively:
#    ./waveform.sh
#  Then type  start  or  stop  at the prompt.
# ════════════════════════════════════════════════════════════════

# ── Configuration (edit these if your setup changes) ─────────────
PORT="/dev/cu.usbserial-0001"
FQBN="esp32:esp32:esp32"
SKETCH="arduino/waveform_eeg_bridge"
VENV=".venv/bin"
APP="app.py"
# ─────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.waveform.pids"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
  echo -e "${CYAN}"
  echo "  ██╗    ██╗ █████╗ ██╗   ██╗███████╗███████╗ ██████╗ ██████╗ ███╗   ███╗"
  echo "  ██║    ██║██╔══██╗██║   ██║██╔════╝██╔════╝██╔═══██╗██╔══██╗████╗ ████║"
  echo "  ██║ █╗ ██║███████║██║   ██║█████╗  █████╗  ██║   ██║██████╔╝██╔████╔██║"
  echo "  ██║███╗██║██╔══██║╚██╗ ██╔╝██╔══╝  ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║"
  echo "  ╚███╔███╔╝██║  ██║ ╚████╔╝ ███████╗██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║"
  echo "   ╚══╝╚══╝ ╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝"
  echo -e "${RESET}  ${BOLD}EEG Brain Monitor${RESET} · ESP32 + ADS1115 + AD8232"
  echo ""
}

cmd_start() {
  echo -e "${BOLD}[1/3]${RESET} 🔨 Compiling and 🔌 Uploading to ESP32..."
  echo -e "      Port: ${CYAN}$PORT${RESET} · Board: ${CYAN}$FQBN${RESET}"
  echo ""

  # Step A: Compile (ensure binaries are fresh)
  arduino-cli compile --fqbn "$FQBN" "$SCRIPT_DIR/$SKETCH" &>/dev/null
  if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Compilation failed. Check your Arduino code.${RESET}"
    return 1
  fi

  # Step B: Upload (Standard arduino-cli)
  echo "      Uploading..."
  echo -e "      ${YELLOW}Note: If it hangs on 'Connecting...', hold the BOOT button on your ESP32.${RESET}"
  arduino-cli upload -p "$PORT" --fqbn "$FQBN" "$SCRIPT_DIR/$SKETCH" --upload-property upload.speed=115200

  if [ $? -ne 0 ]; then
    echo -e "\n${RED}✗ Automatic upload failed.${RESET}"
    echo "  Please ensure the ESP32 is connected and not in use by another app."
    return 1
  fi

  echo -e "\n${GREEN}✓ System ready!${RESET}"
  echo ""
  echo -e "${BOLD}[2/3]${RESET} ⏳ Waiting for ESP32 to boot..."
  sleep 2

  echo -e "${BOLD}[3/3]${RESET} 🚀 Starting WaveForm dashboard..."
  pkill -f "streamlit run $APP" 2>/dev/null
  
  "$SCRIPT_DIR/$VENV/streamlit" run "$SCRIPT_DIR/$APP" \
    --server.headless false \
    --server.port 8501 \
    &>/tmp/waveform_streamlit.log &
  local stream_pid=$!
  echo "$stream_pid" > "$PID_FILE"

  sleep 3
  if kill -0 "$stream_pid" 2>/dev/null; then
    echo -e "${GREEN}✓ Dashboard running at http://localhost:8501${RESET}"
    echo ""
    echo -e "  ${BOLD}Next step in the browser:${RESET}"
    echo -e "  Sidebar → Signal Source → 🔌 Arduino (Serial) → $PORT → Connect"
    echo ""
    echo -e "  ${YELLOW}Type 'stop' and Enter to shut everything down.${RESET}"
    while true; do
      read -r input
      if [ "$input" = "stop" ]; then
        cmd_stop
        break
      fi
    done
  else
    echo -e "${RED}✗ Dashboard failed to start. Check /tmp/waveform_streamlit.log${RESET}"
  fi
}


cmd_stop() {
  echo -e "\n${BOLD}Stopping WaveForm...${RESET}"

  # Kill tracked PIDs
  if [ -f "$PID_FILE" ]; then
    while read -r pid; do
      kill "$pid" 2>/dev/null && echo -e "  ${GREEN}✓ Stopped process $pid${RESET}"
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi

  # Kill any lingering processes by name
  pkill -f "streamlit run $APP" 2>/dev/null
  pkill -f "arduino-cli upload" 2>/dev/null

  echo -e "${GREEN}✓ All WaveForm processes stopped.${RESET}\n"
}

interactive_mode() {
  banner
  echo -e "  Commands: ${BOLD}start${RESET} · ${BOLD}stop${RESET} · ${BOLD}exit${RESET}"
  echo ""
  while true; do
    echo -en "${CYAN}waveform>${RESET} "
    read -r input
    case "$input" in
      start) cmd_start ;;
      stop)  cmd_stop  ;;
      exit|quit) cmd_stop; echo "Goodbye!"; exit 0 ;;
      "") ;;
      *) echo -e "  Unknown command '${input}'. Use: start · stop · exit" ;;
    esac
  done
}

# ── Entry point ─────────────────────────────────────────────────
cd "$SCRIPT_DIR" || exit 1

case "${1:-}" in
  start)
    banner
    cmd_start
    ;;
  stop)
    cmd_stop
    ;;
  "")
    banner
    interactive_mode
    ;;
  *)
    echo "Usage: $0 [start|stop]"
    exit 1
    ;;
esac
