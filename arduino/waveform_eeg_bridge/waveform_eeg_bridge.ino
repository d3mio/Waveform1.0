/*
 * WaveForm EEG Serial Bridge  –  ADS1115 + ESP32 Edition
 * =======================================================
 * Reads EEG data from AD8232 via ADS1115 (16-bit external ADC over I2C)
 * and streams samples at 200 Hz to the WaveForm dashboard.
 *
 * WIRING (as connected)
 * ----------------------
 *   ADS1115 VDD    → 3.3V rail
 *   ADS1115 GND    → GND rail
 *   ADS1115 ADDR   → GND rail    (I2C address = 0x48)
 *   ADS1115 SDA    → ESP32 GPIO 21
 *   ADS1115 SCL    → ESP32 GPIO 22
 *   ADS1115 A0     → AD8232 OUTPUT
 *
 *   AD8232 VIN     → 3.3V rail
 *   AD8232 GND     → GND rail
 *   AD8232 SDN     → 3.3V rail   (keep sensor ON)
 *   AD8232 OUTPUT  → ADS1115 A0
 *   AD8232 LO+     → ESP32 GPIO 2
 *   AD8232 LO-     → ESP32 GPIO 4
 *
 * LIBRARY REQUIRED
 * ----------------
 *   Adafruit ADS1X15  (install via Arduino Library Manager or arduino-cli)
 *   arduino-cli lib install "Adafruit ADS1X15" "Adafruit BusIO"
 *
 * OUTPUT PROTOCOL (115200 baud)
 * ------------------------------
 *   Startup: WAVEFORM_START / ADC_MAX:32767 / FS:200
 *   Samples: one integer per line (signed, centred at ~16384)
 *   Diagnostics: RATE:<ms>  every 200 samples (~1 s)
 */

#include <Adafruit_ADS1X15.h>
#include <Wire.h>

// ── Pins ───────────────────────────────────────────────────────
#define LEAD_OFF_PLUS_PIN 2  // AD8232 LO+
#define LEAD_OFF_MINUS_PIN 4 // AD8232 LO-

// ── Configuration ──────────────────────────────────────────────
#define BAUD_RATE 115200
#define SAMPLE_INTERVAL_US 5000UL // 5000 µs = 200 Hz
#define ADC_MAX 32767             // ADS1115 16-bit signed max

// ── ADC object ─────────────────────────────────────────────────
Adafruit_ADS1115 ads;

// ── State ──────────────────────────────────────────────────────
unsigned long lastSampleTime = 0;
unsigned long sampleCount = 0;
unsigned long lastRateCheck = 0;
bool adsOK = false;

void setup() {
  Serial.begin(BAUD_RATE);

  pinMode(LEAD_OFF_PLUS_PIN, INPUT);
  pinMode(LEAD_OFF_MINUS_PIN, INPUT);

  // I2C on default ESP32 pins (SDA=21, SCL=22)
  Wire.begin(21, 22);

  // Initialise ADS1115 at default I2C address 0x48 (ADDR → GND)
  if (ads.begin(0x48)) {
    adsOK = true;

    // GAIN_ONE  = ±4.096 V full scale  →  good for 3.3V signals
    // Each bit  = 4.096 / 32768 ≈ 125 µV
    ads.setGain(GAIN_ONE);

    // ADS1115 continuous conversion at 250 SPS (> 200 Hz needed)
    ads.setDataRate(RATE_ADS1115_250SPS);
  }

  delay(200);

  // Startup handshake for Python dashboard
  Serial.println("WAVEFORM_START");
  Serial.print("ADC_MAX:");
  Serial.println(ADC_MAX);
  Serial.println("FS:200");
  if (!adsOK) {
    Serial.println("ERROR:ADS1115_NOT_FOUND");
  }

  lastRateCheck = millis();
}

void loop() {
  unsigned long now = micros();

  if (now - lastSampleTime >= SAMPLE_INTERVAL_US) {
    lastSampleTime = now;
    sampleCount++;

    int sample;

    if (!adsOK) {
      // ADS1115 not found – send mid-scale so dashboard doesn't crash
      sample = ADC_MAX / 2;
    } else {
      bool leadOff =
          digitalRead(LEAD_OFF_PLUS_PIN) || digitalRead(LEAD_OFF_MINUS_PIN);

      if (leadOff) {
        sample = ADC_MAX / 2; // mid-scale when electrodes off
      } else {
        // Read channel A0 (single-ended vs GND)
        sample = (int)ads.readADC_SingleEnded(0);
        // Clamp to valid range
        if (sample < 0)
          sample = 0;
        if (sample > ADC_MAX)
          sample = ADC_MAX;
      }
    }

    Serial.println(sample);

    // Every 200 samples: report timing accuracy (~1000 ms expected)
    if (sampleCount % 200 == 0) {
      unsigned long elapsed = millis() - lastRateCheck;
      Serial.print("RATE:");
      Serial.println(elapsed);
      lastRateCheck = millis();
    }
  }
}
