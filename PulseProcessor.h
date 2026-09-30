// PulseProcessor.h
// Heart-rate extraction from raw MAX30100 IR samples.
// Pure C++ with no Arduino dependencies, so it can be unit-tested on a PC.
//
// Pipeline: DC removal (1st-order high-pass) -> 2nd-order Butterworth
// low-pass -> slope (first difference) -> adaptive-threshold detection of
// the systolic upstroke -> interval validation -> moving average of the
// last 4 beat intervals.

#pragma once
#include <stdint.h>

class PulseProcessor {
public:
    void begin(float sampleRateHz, float lowpassHz, uint16_t fingerThreshold);

    // Feed one raw IR sample with its timestamp. Returns true on a new beat.
    bool update(uint16_t rawIr, uint32_t tMs);

    float bpm() const          { return bpm_; }
    bool  fingerPresent() const{ return finger_; }
    float filtered() const     { return y_; }

private:
    static const uint8_t N_AVG = 4;

    void reset();

    // DC removal
    float dc_ = 0; bool dcInit_ = false; float dcAlpha_ = 0.01f;
    // Butterworth low-pass (direct form II transposed)
    float b0_ = 0, b1_ = 0, b2_ = 0, a1_ = 0, a2_ = 0, z1_ = 0, z2_ = 0;
    // Peak detection
    float y_ = 0, d_ = 0, d1_ = 0, d2_ = 0, env_ = 0;
    uint32_t lastBeatMs_ = 0; bool haveBeat_ = false;
    // Beat averaging
    float intervals_[N_AVG] = {0};
    uint8_t count_ = 0, idx_ = 0, rejects_ = 0;
    float bpm_ = 0;
    // Finger detection
    uint16_t fingerThreshold_ = 10000; bool finger_ = false;
};
