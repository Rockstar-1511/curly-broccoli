// MAX30100.cpp
#include "MAX30100.h"
#include <Wire.h>

static const uint8_t ADDR          = 0x57;
static const uint8_t REG_FIFO_WR   = 0x02;
static const uint8_t REG_FIFO_OVF  = 0x03;
static const uint8_t REG_FIFO_RD   = 0x04;
static const uint8_t REG_FIFO_DATA = 0x05;
static const uint8_t REG_MODE      = 0x06;
static const uint8_t REG_SPO2      = 0x07;
static const uint8_t REG_LED       = 0x09;
static const uint8_t REG_PART_ID   = 0xFF;
static const uint8_t PART_ID       = 0x11;

bool MAX30100::begin(uint8_t irCurrent) {
    Wire.begin();
    Wire.setClock(400000);
    if (readReg(REG_PART_ID) != PART_ID) return false;

    writeReg(REG_MODE, 0x40);                 // reset
    delay(10);
    writeReg(REG_MODE, 0x02);                 // heart-rate mode (IR only)
    writeReg(REG_SPO2, 0x40 | (0x01 << 2) | 0x03); // HI_RES, 100 sps, 1600 us
    writeReg(REG_LED, irCurrent & 0x0F);      // red off, IR current
    writeReg(REG_FIFO_WR, 0);
    writeReg(REG_FIFO_OVF, 0);
    writeReg(REG_FIFO_RD, 0);
    return true;
}

uint8_t MAX30100::readFifo(uint16_t* irOut, uint8_t maxSamples, uint8_t* lost) {
    const uint8_t wr  = readReg(REG_FIFO_WR);
    const uint8_t ovf = readReg(REG_FIFO_OVF);
    const uint8_t rd  = readReg(REG_FIFO_RD);
    uint8_t n = (wr - rd) & 0x0F;             // 16-sample FIFO
    if (ovf) n = 16;
    *lost = ovf;
    if (n > maxSamples) n = maxSamples;

    uint8_t done = 0;
    while (done < n) {
        uint8_t chunk = n - done;
        if (chunk > 8) chunk = 8;             // Wire buffer is 32 bytes = 8 samples
        Wire.beginTransmission(ADDR);
        Wire.write(REG_FIFO_DATA);
        Wire.endTransmission(false);
        Wire.requestFrom(ADDR, (uint8_t)(chunk * 4));
        for (uint8_t i = 0; i < chunk; i++) {
            const uint8_t irH = Wire.read(), irL = Wire.read();
            Wire.read(); Wire.read();         // red channel, unused in HR mode
            irOut[done++] = ((uint16_t)irH << 8) | irL;
        }
    }
    return n;
}

void MAX30100::writeReg(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(ADDR);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

uint8_t MAX30100::readReg(uint8_t reg) {
    Wire.beginTransmission(ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(ADDR, (uint8_t)1);
    return Wire.available() ? Wire.read() : 0;
}
