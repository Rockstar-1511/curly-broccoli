// TemperatureSensor.h
// LM35 temperature reading with signal conditioning:
//  - 1.1 V internal ADC reference: ~0.107 C per LSB instead of ~0.49 C with 5 V
//  - 16x oversampling to average out ADC noise
//  - exponential moving average for a stable reading
// LM35 output is 10 mV/C, so the 1.1 V reference covers 0-110 C.

#pragma once
#include <Arduino.h>

class TemperatureSensor {
public:
    void  begin(uint8_t pin, float offsetC);
    float update();                 // call about once per second
    float celsius() const { return value_; }

private:
    uint8_t pin_ = A0;
    float offset_ = 0, value_ = 0;
    bool init_ = false;
};
