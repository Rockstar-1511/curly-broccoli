// AlertManager.h
// Decides when to send an emergency SMS. Pure C++ (unit-testable).
// A condition must persist for sustainMs before it triggers, and each alert
// type has a cooldown so a single event does not send repeated messages.

#pragma once
#include <stdint.h>

enum AlertType : uint8_t { ALERT_NONE = 0, ALERT_HR_LOW, ALERT_HR_HIGH, ALERT_TEMP_HIGH, ALERT_COUNT };

class AlertManager {
public:
    void begin(float hrLow, float hrHigh, float tempHigh, uint32_t sustainMs, uint32_t cooldownMs);

    // Call once per second. Returns the alert to send now, or ALERT_NONE.
    AlertType evaluate(float bpm, bool bpmValid, float tempC, uint32_t nowMs);

    static const char* name(AlertType a);

private:
    bool check(AlertType a, bool active, uint32_t nowMs);

    float hrLow_ = 50, hrHigh_ = 120, tempHigh_ = 38;
    uint32_t sustainMs_ = 10000, cooldownMs_ = 300000;
    uint32_t since_[ALERT_COUNT] = {0};
    uint32_t lastSent_[ALERT_COUNT] = {0};
    bool     active_[ALERT_COUNT] = {false};
    bool     sentOnce_[ALERT_COUNT] = {false};
};
