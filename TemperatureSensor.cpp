// TemperatureSensor.cpp
#include "TemperatureSensor.h"

static const uint8_t OVERSAMPLE = 16;
static const float   EMA_ALPHA  = 0.2f;
static const float   VREF_MV    = 1100.0f;   // nominal; measure your chip's value for best accuracy

void TemperatureSensor::begin(uint8_t pin, float offsetC) {
    pin_ = pin; offset_ = offsetC;
    analogReference(INTERNAL);
    analogRead(pin_);                        // first read after a reference change is unreliable
    delay(10);
}

float TemperatureSensor::update() {
    uint16_t sum = 0;
    for (uint8_t i = 0; i < OVERSAMPLE; i++) sum += analogRead(pin_);
    const float mv = (sum / (float)OVERSAMPLE) * VREF_MV / 1024.0f;
    const float c  = mv / 10.0f + offset_;
    value_ = init_ ? value_ + EMA_ALPHA * (c - value_) : c;
    init_ = true;
    return value_;
}
