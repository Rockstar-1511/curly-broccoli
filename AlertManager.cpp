// AlertManager.cpp
#include "AlertManager.h"

void AlertManager::begin(float hrLow, float hrHigh, float tempHigh, uint32_t sustainMs, uint32_t cooldownMs) {
    hrLow_ = hrLow; hrHigh_ = hrHigh; tempHigh_ = tempHigh;
    sustainMs_ = sustainMs; cooldownMs_ = cooldownMs;
}

bool AlertManager::check(AlertType a, bool cond, uint32_t now) {
    if (!cond) { active_[a] = false; return false; }
    if (!active_[a]) { active_[a] = true; since_[a] = now; }
    if (now - since_[a] < sustainMs_) return false;
    if (sentOnce_[a] && (now - lastSent_[a]) < cooldownMs_) return false;
    sentOnce_[a] = true;
    lastSent_[a] = now;
    return true;
}

AlertType AlertManager::evaluate(float bpm, bool bpmValid, float tempC, uint32_t now) {
    // Evaluate every condition so each timer stays current, then report the first due
    const bool low  = check(ALERT_HR_LOW,    bpmValid && bpm < hrLow_,  now);
    const bool high = check(ALERT_HR_HIGH,   bpmValid && bpm > hrHigh_, now);
    const bool temp = check(ALERT_TEMP_HIGH, tempC > tempHigh_,         now);
    if (low)  return ALERT_HR_LOW;
    if (high) return ALERT_HR_HIGH;
    if (temp) return ALERT_TEMP_HIGH;
    return ALERT_NONE;
}

const char* AlertManager::name(AlertType a) {
    switch (a) {
        case ALERT_HR_LOW:    return "LOW HEART RATE";
        case ALERT_HR_HIGH:   return "HIGH HEART RATE";
        case ALERT_TEMP_HIGH: return "HIGH TEMPERATURE";
        default:              return "NONE";
    }
}
