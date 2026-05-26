#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>

Adafruit_ADS1115 ads;
BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;

// MISSION UUIDS
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) { deviceConnected = true; };
    void onDisconnect(BLEServer* pServer) { 
        deviceConnected = false;
        BLEDevice::startAdvertising(); // Auto-restart advertising
    }
};

void setup() {
  Serial.begin(115200);
  pinMode(2, OUTPUT); // Blue LED Heartbeat

  if (!ads.begin()) {
    Serial.println("ADS1115 failed!");
    while (1) { digitalWrite(2, !digitalRead(2)); delay(100); } // Rapid flash = Error
  }
  ads.setGain(GAIN_ONE);

  // Initialize BLE
  BLEDevice::init("WaveForm_EEG_Pro");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_INDICATE
                    );
  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();

  // Optimized Advertising for Apple Devices
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  // Apple connection interval
  pAdvertising->setMinPreferred(0x12);
  
  delay(1000); // Wait for radio
  pAdvertising->start();
  Serial.println("WaveForm_EEG_Pro: ADVERTISING STARTED.");
}

void loop() {
    static unsigned long lastNotify = 0;
    static bool ledState = false;

    if (deviceConnected) {
        if (millis() - lastNotify > 15) { // ~60Hz
            lastNotify = millis();
            int16_t adc0 = ads.readADC_SingleEnded(0);
            pCharacteristic->setValue((uint8_t*)&adc0, 2); // Binary send for speed
            pCharacteristic->notify();
            
            // Fast Pulse when streaming
            digitalWrite(2, ledState); ledState = !ledState;
        }
    } else {
        // Slow Pulse when advertising
        if (millis() % 1000 < 100) digitalWrite(2, HIGH); else digitalWrite(2, LOW);
    }
}
