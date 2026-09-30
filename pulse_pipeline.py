"""Python mirror of the firmware PulseProcessor, used for analysis and plots.

Keep this file in step with firmware/health_monitor/PulseProcessor.cpp.
test/compare_with_firmware.py checks both give the same BPM output.
"""
import math

REFRACTORY_MS, MIN_IBI_MS, MAX_IBI_MS = 300, 273, 2000
MAX_JUMP, ENV_DECAY, THRESH_FRAC, N_AVG = 0.30, 0.995, 0.5, 4


class PulseProcessor:
    def __init__(self, fs=100.0, fc=4.0, finger_threshold=10000, dc_alpha=0.03):
        self.finger_threshold = finger_threshold
        self.dc_alpha = dc_alpha
        K = math.tan(math.pi * fc / fs)
        norm = 1 / (1 + math.sqrt(2) * K + K * K)
        self.b0 = K * K * norm; self.b1 = 2 * self.b0; self.b2 = self.b0
        self.a1 = 2 * (K * K - 1) * norm; self.a2 = (1 - math.sqrt(2) * K + K * K) * norm
        self.reset()
        self.trace_y, self.trace_thr = [], []

    def reset(self):
        self.dc = None; self.z1 = self.z2 = 0.0
        self.y = self.d = self.d1 = self.d2 = self.env = 0.0
        self.last_beat = None; self.intervals = []; self.idx = 0; self.rejects = 0; self.bpm = 0.0

    def update(self, raw, t_ms):
        self.finger = raw > self.finger_threshold
        if not self.finger:
            self.reset(); return False
        if self.dc is None: self.dc = float(raw)
        self.dc += self.dc_alpha * (raw - self.dc)
        x = self.dc - raw
        y = self.b0 * x + self.z1
        self.z1 = self.b1 * x - self.a1 * y + self.z2
        self.z2 = self.b2 * x - self.a2 * y
        # Slope of the filtered pulse: the systolic upstroke is sharp, while
        # respiration and drift are slow, so the derivative suppresses wander
        d = y - self.y
        self.y = y
        self.d2, self.d1, self.d = self.d1, self.d, d
        self.env = d if d > self.env else self.env * ENV_DECAY
        self.trace_y.append(d); self.trace_thr.append(THRESH_FRAC * self.env)

        if not (self.d1 > self.d2 and self.d1 >= self.d and self.d1 > THRESH_FRAC * self.env):
            return False
        if self.last_beat is not None and t_ms - self.last_beat < REFRACTORY_MS:
            return False
        new = False
        if self.last_beat is not None:
            ibi = t_ms - self.last_beat
            if MIN_IBI_MS <= ibi <= MAX_IBI_MS:
                n = len(self.intervals)
                avg = sum(self.intervals) / n if n else 0
                outlier = n == N_AVG and abs(ibi - avg) > MAX_JUMP * avg
                if outlier:
                    self.rejects += 1
                if not outlier or self.rejects >= 3:
                    if outlier: self.intervals = []; self.idx = 0
                    self.rejects = 0
                    if len(self.intervals) < N_AVG: self.intervals.append(ibi)
                    else: self.intervals[self.idx] = ibi
                    self.idx = (self.idx + 1) % N_AVG
                    self.bpm = 60000 * len(self.intervals) / sum(self.intervals)
                    new = True
        self.last_beat = t_ms
        return new


class AlertManager:
    """Python mirror of firmware AlertManager (sustain time + cooldown)."""
    NAMES = {1: "LOW HEART RATE", 2: "HIGH HEART RATE", 3: "HIGH TEMPERATURE"}

    def __init__(self, hr_low=50, hr_high=120, temp_high=38.0, sustain_ms=10000, cooldown_ms=300000):
        self.hr_low, self.hr_high, self.temp_high = hr_low, hr_high, temp_high
        self.sustain, self.cooldown = sustain_ms, cooldown_ms
        self.since, self.last_sent, self.active = {}, {}, {}

    def _check(self, a, cond, now):
        if not cond:
            self.active[a] = False
            return False
        if not self.active.get(a):
            self.active[a] = True; self.since[a] = now
        if now - self.since[a] < self.sustain:
            return False
        if a in self.last_sent and now - self.last_sent[a] < self.cooldown:
            return False
        self.last_sent[a] = now
        return True

    def evaluate(self, bpm, bpm_valid, temp_c, now):
        low = self._check(1, bpm_valid and bpm < self.hr_low, now)
        high = self._check(2, bpm_valid and bpm > self.hr_high, now)
        temp = self._check(3, temp_c > self.temp_high, now)
        return 1 if low else 2 if high else 3 if temp else 0


class TemperatureConditioner:
    """Python mirror of firmware TemperatureSensor (1.1 V ref, 16x oversample, EMA)."""

    def __init__(self, offset_c=0.0, alpha=0.2, vref_mv=1100.0):
        self.offset, self.alpha, self.vref = offset_c, alpha, vref_mv
        self.value = None

    def update(self, codes):
        c = (sum(codes) / len(codes)) * self.vref / 1024 / 10 + self.offset
        self.value = c if self.value is None else self.value + self.alpha * (c - self.value)
        return self.value
