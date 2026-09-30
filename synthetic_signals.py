"""Synthetic test signals for the monitoring pipeline.

Generates a realistic MAX30100 IR signal (DC level, pulse waveform with
dicrotic notch, heart-rate variability, respiration baseline wander, noise,
and motion artefacts) plus an LM35 ADC signal, following a scripted scenario
with normal, tachycardia and fever periods.
"""
import numpy as np

FS = 100.0          # MAX30100 sample rate (Hz)
DURATION = 240.0    # seconds


def true_heart_rate(t):
    """Scenario: rest 72 BPM, exercise-like rise to 132 BPM, recovery to 80 BPM."""
    return np.interp(t, [0, 50, 80, 130, 160, 240], [72, 72, 132, 132, 80, 80])


def true_temperature(t):
    """Scenario: 36.8 C, rising to a 38.6 C fever, then settling at 38.3 C."""
    return np.interp(t, [0, 120, 170, 240], [36.8, 36.8, 38.6, 38.3])


def ppg_signal(seed=7):
    rng = np.random.default_rng(seed)
    t = np.arange(0, DURATION, 1 / FS)
    hr = true_heart_rate(t)
    # Heart-rate variability: slow modulation of the beat rate
    inst = hr / 60 * (1 + 0.03 * np.sin(2 * np.pi * 0.1 * t))
    phase = np.cumsum(inst) / FS
    frac = phase % 1.0
    # Pulse shape: systolic peak + dicrotic wave (blood volume, arbitrary units)
    pulse = np.exp(-((frac - 0.15) / 0.07) ** 2) + 0.35 * np.exp(-((frac - 0.45) / 0.09) ** 2)
    dc = 42000 + 300 * np.sin(2 * np.pi * 0.25 * t) + 300 * np.sin(2 * np.pi * 0.02 * t)
    ir = dc - 250 * pulse + rng.normal(0, 12, t.size)
    # Motion artefacts: short bursts
    for t0 in (30, 100, 200):
        m = (t > t0) & (t < t0 + 1.5)
        ir[m] += 600 * np.sin(2 * np.pi * 3.3 * (t[m] - t0)) * np.hanning(m.sum())
    beats = np.flatnonzero(np.diff(np.floor(phase)) > 0) / FS
    return t, np.clip(ir, 0, 65535).astype(np.uint16), hr, beats


def lm35_adc(seed=3):
    """LM35 (10 mV/C) read by a 10-bit ADC with the 1.1 V internal reference."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, DURATION, 1.0)
    temp = true_temperature(t)
    # 16 raw readings per second with ~1.5 LSB noise and a 0.3 C sensor offset
    mv = (temp + 0.3)[:, None] * 10 + rng.normal(0, 1.6, (t.size, 16))
    codes = np.clip(np.round(mv / 1100 * 1024), 0, 1023)
    return t, temp, codes


if __name__ == "__main__":
    t, ir, hr, _ = ppg_signal()
    np.savetxt("ppg_input.csv", np.column_stack([np.round(t * 1000).astype(int), ir]),
               fmt="%d", delimiter=",", header="time_ms,ir", comments="")
    print(f"wrote ppg_input.csv ({t.size} samples)")
