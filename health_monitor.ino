// Heart Rate & Temperature Monitoring System
// ATmega328P (Arduino Uno/Nano) + MAX30100 + LM35 + SIM800L
//
// Samples the MAX30100 at 100 sps, extracts heart rate, reads the LM35 once
// per second, logs CSV over serial, and sends an SMS when a vital sign stays
// outside its safe range. Not a medical device: for learning and prototyping only.
//
// Requires human review and hardware testing before any real use.

#if __has_include("config.h")
#include "config.h"
#else
#error "Copy config.example.h to config.h and set your values before compiling."
#endif

#include "MAX30100.h"
#include "PulseProcessor.h"
#include "TemperatureSensor.h"
#include "AlertManager.h"
#include "GsmAlert.h"

// ---- Pins --------------------------------------------------------------
const uint8_t PIN_LM35     = A0;
const uint8_t PIN_GSM_RX   = 7;    // to SIM800L TX
const uint8_t PIN_GSM_TX   = 8;    // to SIM800L RX (use a level divider)
const uint8_t PIN_BUZZER   = 9;
const uint8_t PIN_BEAT_LED = 13;

const float    SAMPLE_RATE_HZ = 100.0f;
const float    LOWPASS_HZ     = 4.0f;
const uint32_t SAMPLE_MS      = 10;
const uint32_t LOG_PERIOD_MS  = 1000;

MAX30100          pulseSensor;
PulseProcessor    pulse;
TemperatureSensor temp;
AlertManager      alerts;
GsmAlert          gsm(PIN_GSM_RX, PIN_GSM_TX);

uint32_t sampleClockMs = 0;        // time base from the sample count (100 sps)
uint32_t lastLogMs = 0;
uint32_t beatLedOffMs = 0;

void setup() {
    Serial.begin(115200);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_BEAT_LED, OUTPUT);

    if (!pulseSensor.begin(IR_LED_CURRENT)) {
        Serial.println(F("# ERROR: MAX30100 not found. Check wiring and I2C pull-ups."));
    }
    pulse.begin(SAMPLE_RATE_HZ, LOWPASS_HZ, FINGER_THRESHOLD);
    temp.begin(PIN_LM35, TEMP_OFFSET_C);
    alerts.begin(HR_LOW_BPM, HR_HIGH_BPM, TEMP_HIGH_C, ALERT_SUSTAIN_MS, ALERT_COOLDOWN_MS);
    gsm.begin(ALERT_PHONE_NUMBER);

    Serial.println(F("time_ms,bpm,temp_c,finger,alert"));
}

void loop() {
    // 1) Pulse sensor: drain the FIFO and process every sample
    uint16_t ir[16];
    uint8_t lost = 0;
    const uint8_t n = pulseSensor.readFifo(ir, 16, &lost);
    sampleClockMs += (uint32_t)lost * SAMPLE_MS;
    for (uint8_t i = 0; i < n; i++) {
        sampleClockMs += SAMPLE_MS;
        if (pulse.update(ir[i], sampleClockMs)) {
            digitalWrite(PIN_BEAT_LED, HIGH);
            beatLedOffMs = millis() + 50;
        }
    }
    if ((int32_t)(millis() - beatLedOffMs) >= 0) digitalWrite(PIN_BEAT_LED, LOW);

    // 2) Once per second: temperature, alerts, logging
    const uint32_t now = millis();
    if (now - lastLogMs >= LOG_PERIOD_MS) {
        lastLogMs = now;
        const float tC = temp.update();
        const bool valid = pulse.fingerPresent() && pulse.bpm() > 0;

        const AlertType a = alerts.evaluate(pulse.bpm(), valid, tC, now);
        if (a != ALERT_NONE) {
            char msg[100], tBuf[8];
            dtostrf(tC, 4, 1, tBuf);
            snprintf(msg, sizeof(msg), "ALERT: %s. HR %d BPM, Temp %s C",
                     AlertManager::name(a), (int)(pulse.bpm() + 0.5f), tBuf);
            gsm.send(msg);
            tone(PIN_BUZZER, 2000, 500);
        }

        Serial.print(now);                 Serial.print(',');
        Serial.print(valid ? pulse.bpm() : 0, 1); Serial.print(',');
        Serial.print(tC, 2);               Serial.print(',');
        Serial.print(pulse.fingerPresent()); Serial.print(',');
        Serial.println(a);
    }

    // 3) Advance the SMS state machine without blocking
    gsm.poll();
}
