// MAX30100.h
// Minimal register-level driver for the MAX30100 pulse oximeter (I2C 0x57).
// Heart-rate mode (IR LED only), 100 samples/s, 1600 us pulse width, 16-bit ADC.
// Register map: Maxim Integrated MAX30100 datasheet. Verify against your
// datasheet revision before changing settings.

#pragma once
#include <Arduino.h>

class MAX30100 {
public:
    bool begin(uint8_t irCurrent);
    // Reads new FIFO samples into irOut (up to maxSamples). Returns count read.
    uint8_t readFifo(uint16_t* irOut, uint8_t maxSamples, uint8_t* lostSamples);

private:
    void    writeReg(uint8_t reg, uint8_t value);
    uint8_t readReg(uint8_t reg);
};
