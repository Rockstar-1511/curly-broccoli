// PulseProcessor.cpp
#include "PulseProcessor.h"
#include <math.h>

static const uint32_t REFRACTORY_MS = 300;   // max 200 BPM
static const uint32_t MIN_IBI_MS    = 273;   // 220 BPM
static const uint32_t MAX_IBI_MS    = 2000;  // 30 BPM
static const float    MAX_JUMP      = 0.30f; // reject beats >30% off the average
static const float    ENV_DECAY     = 0.995f;
static const float    THRESH_FRAC   = 0.5f;

void PulseProcessor::begin(float fs, float fc, uint16_t fingerThreshold) {
    fingerThreshold_ = fingerThreshold;
    // High-pass corner ~0.5 Hz at 100 Hz: removes DC, drift and most respiration wander
    dcAlpha_ = 0.03f;

    // Butterworth low-pass via bilinear transform with pre-warping
    const float K = tanf(3.14159265f * fc / fs);
    const float norm = 1.0f / (1.0f + 1.41421356f * K + K * K);
    b0_ = K * K * norm;
    b1_ = 2.0f * b0_;
    b2_ = b0_;
    a1_ = 2.0f * (K * K - 1.0f) * norm;
    a2_ = (1.0f - 1.41421356f * K + K * K) * norm;
    reset();
}

void PulseProcessor::reset() {
    dcInit_ = false; z1_ = z2_ = 0; y_ = d_ = d1_ = d2_ = env_ = 0;
    haveBeat_ = false; count_ = idx_ = rejects_ = 0; bpm_ = 0;
}

bool PulseProcessor::update(uint16_t raw, uint32_t tMs) {
    finger_ = raw > fingerThreshold_;
    if (!finger_) { reset(); return false; }

    if (!dcInit_) { dc_ = raw; dcInit_ = true; }
    dc_ += dcAlpha_ * ((float)raw - dc_);
    // Blood volume increase absorbs more IR, so invert: peaks = heartbeats
    const float x = dc_ - (float)raw;

    const float y = b0_ * x + z1_;
    z1_ = b1_ * x - a1_ * y + z2_;
    z2_ = b2_ * x - a2_ * y;

    // Slope of the filtered pulse: the systolic upstroke is sharp, while
    // respiration and drift are slow, so the derivative suppresses wander
    const float d = y - y_;
    y_ = y;
    d2_ = d1_; d1_ = d_; d_ = d;

    env_ = (d > env_) ? d : env_ * ENV_DECAY;

    // Steepest upstroke (local max of slope) above the adaptive threshold
    const bool isPeak = (d1_ > d2_) && (d1_ >= d_) && (d1_ > THRESH_FRAC * env_);
    if (!isPeak) return false;

    const uint32_t tPeak = tMs;   // one-sample (10 ms) offset is the same for every beat
    if (haveBeat_ && (tPeak - lastBeatMs_) < REFRACTORY_MS) return false;

    bool newBeat = false;
    if (haveBeat_) {
        const uint32_t ibi = tPeak - lastBeatMs_;
        if (ibi >= MIN_IBI_MS && ibi <= MAX_IBI_MS) {
            float avg = 0;
            for (uint8_t i = 0; i < count_; i++) avg += intervals_[i];
            if (count_) avg /= count_;

            const bool outlier = count_ == N_AVG && fabsf(ibi - avg) > MAX_JUMP * avg;
            if (!outlier || ++rejects_ >= 3) {
                if (outlier) { count_ = 0; idx_ = 0; }  // sustained change: re-learn
                rejects_ = 0;
                intervals_[idx_] = (float)ibi;
                idx_ = (idx_ + 1) % N_AVG;
                if (count_ < N_AVG) count_++;
                float sum = 0;
                for (uint8_t i = 0; i < count_; i++) sum += intervals_[i];
                bpm_ = 60000.0f * count_ / sum;
                newBeat = true;
            }
        }
    }
    lastBeatMs_ = tPeak;
    haveBeat_ = true;
    return newBeat;
}
