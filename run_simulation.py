"""Run the full monitoring pipeline on synthetic signals and save figures.

Usage (from the repo root):  python simulation/run_simulation.py
Outputs go to results/. Signals are synthetic, not patient data.
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.dirname(__file__))
from synthetic_signals import FS, ppg_signal, lm35_adc, true_heart_rate  # noqa: E402
from pulse_pipeline import PulseProcessor, AlertManager, TemperatureConditioner  # noqa: E402

OUT = "results"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 150, "font.size": 11, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})
C = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]
ARTEFACTS = (30, 100, 200)

# ---------------------------------------------------------------- pulse
t, ir, hr_true, beats = ppg_signal()
t_ms = np.round(t * 1000).astype(int)
pp = PulseProcessor()
det, log_t, log_bpm = [], [], []
for ti, v in zip(t_ms, ir):
    if pp.update(int(v), int(ti)):
        det.append(ti / 1000)
    if ti % 1000 == 0 and ti > 0:
        log_t.append(ti / 1000); log_bpm.append(pp.bpm)
log_t, log_bpm = np.array(log_t), np.array(log_bpm)
slope, thr = np.array(pp.trace_y), np.array(pp.trace_thr)


def reference_bpm(tt):
    """What a reference monitor shows: average of the last 4 true beat intervals."""
    b = beats[beats <= tt]
    return 60 / np.mean(np.diff(b[-5:])) if len(b) > 5 else np.nan


ref = np.array([reference_bpm(x) for x in log_t])
valid = (log_t > 10) & (log_bpm > 0) & ~np.isnan(ref)
err = log_bpm[valid] - ref[valid]
near_art = np.zeros(valid.sum(), bool)
for a in ARTEFACTS:
    near_art |= (log_t[valid] >= a) & (log_t[valid] <= a + 6)

# ---------------------------------------------------------------- temperature
tt, temp_true, codes = lm35_adc()
cond = TemperatureConditioner(offset_c=-0.3)          # offset from calibration
temp_meas = np.array([cond.update(c) for c in codes])
rng = np.random.default_rng(11)
raw5v = np.round(((temp_true + 0.3) * 10 + rng.normal(0, 1.6, tt.size)) / 5000 * 1024) * 5000 / 1024 / 10
terr = temp_meas[5:] - temp_true[5:]

# ---------------------------------------------------------------- alerts
am = AlertManager()
alerts = []
for x, b, tc in zip(log_t, log_bpm, temp_meas[1:len(log_t) + 1]):
    a = am.evaluate(b, b > 0, tc, int(x * 1000))
    if a:
        alerts.append((x, a))

# ================================================================ figures
# 1) Block diagram
fig, ax = plt.subplots(figsize=(13, 5)); ax.axis("off"); ax.set_xlim(0, 13); ax.set_ylim(0, 5)
def box(x, y, w, h, title, sub, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.05", fc=fc, ec=ec, lw=1.8))
    ax.text(x + w / 2, y + h * .68, title, ha="center", va="center", fontweight="bold", fontsize=10)
    ax.text(x + w / 2, y + h * .3, sub, ha="center", va="center", fontsize=8.5, color="#333")
def arrow(x1, y1, x2, y2, label=None):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#555"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + .15, label, ha="center", fontsize=8.5, color="#555")
box(.2, 3.1, 2.2, 1.3, "MAX30100", "pulse sensor\nIR LED, 100 sps", "#EAF0F8", C[0])
box(.2, .6, 2.2, 1.3, "LM35", "temperature\n10 mV/°C", "#EAF0F8", C[0])
box(4.2, 1.5, 3.2, 2.2, "ATmega328P", "HPF + Butterworth LPF\nslope peak detection\n1.1 V ref · 16x oversample · EMA\nalert logic", "#FDF0E6", C[1])
box(9.2, 3.5, 2.4, 1.1, "SIM800L GSM", "emergency SMS", "#F7ECEC", C[3])
box(9.2, 2.05, 2.4, 1.1, "Serial CSV log", "PC logger (Python)", "#EEF6EE", C[2])
box(9.2, .6, 2.4, 1.1, "Buzzer + LED", "local alarm, beat", "#EEF6EE", C[2])
arrow(2.45, 3.75, 4.15, 3.0, "I²C"); arrow(2.45, 1.25, 4.15, 2.1, "ADC A0")
arrow(7.45, 3.2, 9.15, 4.05, "UART"); arrow(7.45, 2.6, 9.15, 2.6, "USB serial"); arrow(7.45, 2.0, 9.15, 1.15, "GPIO")
ax.text(6.5, 4.75, "Heart Rate & Temperature Monitoring System", ha="center", fontsize=13, fontweight="bold")
fig.savefig(f"{OUT}/block_diagram.png", bbox_inches="tight"); plt.close()

# 2) Signal pipeline
m = (t > 12) & (t < 18)
fig, axs = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
axs[0].plot(t[m], ir[m], color=C[0]); axs[0].set(ylabel="Raw IR (counts)", title="1. Raw MAX30100 IR signal: DC level, respiration wander, noise")
filt = np.zeros(t.size); p2 = PulseProcessor(); ys = []
for ti, v in zip(t_ms, ir):
    p2.update(int(v), int(ti)); ys.append(p2.y)
ys = np.array(ys)
axs[1].plot(t[m], ys[m], color=C[1]); axs[1].set(ylabel="Filtered", title="2. After high-pass (DC removal) and 4 Hz Butterworth low-pass")
axs[2].plot(t[m], slope[m], color=C[2], label="Slope"); axs[2].plot(t[m], thr[m], "--", color="gray", label="Adaptive threshold")
d = np.array(det); dm = d[(d > 12) & (d < 18)]
axs[2].plot(dm, np.interp(dm, t, slope) , "v", color=C[3], ms=9, label="Detected beat")
for b in beats[(beats > 12) & (beats < 18)]:
    for a in axs: a.axvline(b, color=C[4], alpha=.15, lw=4)
axs[2].set(xlabel="Time (s)", ylabel="Slope", title="3. Slope peak detection (shaded = true beat onsets)"); axs[2].legend(loc="upper right", fontsize=9, ncol=3)
for a in axs: a.grid(alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/signal_pipeline.png", bbox_inches="tight"); plt.close()

# 3) Filter response
f = np.logspace(-2, np.log10(50), 1000); z = np.exp(1j * 2 * np.pi * f / FS)
a = pp.dc_alpha; Hhp = (1 - a) * (1 - 1 / z) / (1 - (1 - a) / z)
Hlp = (pp.b0 + pp.b1 / z + pp.b2 / z**2) / (1 + pp.a1 / z + pp.a2 / z**2)
H = Hhp * Hlp
fig, ax = plt.subplots(figsize=(10, 5))
ax.semilogx(f, 20 * np.log10(np.maximum(np.abs(H), 1e-6)), color=C[0], lw=2)
ax.axvspan(0.5, 3.7, color=C[2], alpha=.1); ax.text(1.35, -33, "heart-rate band\n30–220 BPM", ha="center", color=C[2])
ax.axvline(0.25, color=C[3], ls=":"); ax.text(0.26, -45, "respiration", color=C[3], fontsize=9)
ax.set(xlabel="Frequency (Hz)", ylabel="Gain (dB)", ylim=(-60, 5), title="Pulse filter response: 0.5 Hz high-pass + 4 Hz Butterworth low-pass")
ax.grid(alpha=.3, which="both"); fig.tight_layout(); fig.savefig(f"{OUT}/filter_response.png", bbox_inches="tight"); plt.close()

# 4) Heart-rate tracking
fig, axs = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw=dict(height_ratios=[2, 1]))
axs[0].plot(log_t, ref, color="gray", lw=3, alpha=.6, label="Reference (true beats)")
axs[0].plot(log_t[log_bpm > 0], log_bpm[log_bpm > 0], color=C[0], lw=1.6, label="Device estimate")
axs[0].axhline(120, color=C[3], ls="--"); axs[0].text(2, 122, "alert threshold 120 BPM", color=C[3], fontsize=9)
for a0 in ARTEFACTS:
    for a in axs: a.axvspan(a0, a0 + 1.5, color=C[1], alpha=.2)
axs[0].text(ARTEFACTS[0] + 2, 60, "motion\nartefact", color=C[1], fontsize=9)
axs[0].set(ylabel="Heart rate (BPM)", ylim=(50, 150), title="Heart-rate tracking during a 72 → 132 → 80 BPM scenario"); axs[0].legend(loc="upper right")
axs[1].plot(log_t[valid], err, color=C[0]); axs[1].axhspan(-2, 2, color=C[2], alpha=.15)
axs[1].set(xlabel="Time (s)", ylabel="Error (BPM)", ylim=(-10, 10)); axs[1].text(2, 2.5, "±2 BPM", color=C[2], fontsize=9)
for a in axs: a.grid(alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/heart_rate_tracking.png", bbox_inches="tight"); plt.close()

# 5) Temperature conditioning
fig, axs = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw=dict(height_ratios=[2, 1]))
axs[0].plot(tt, raw5v, ".", color=C[1], ms=4, alpha=.6, label="Single read, 5 V reference (0.49 °C steps)")
axs[0].plot(tt, temp_meas, color=C[0], lw=2, label="1.1 V ref + 16x oversampling + EMA + calibration")
axs[0].plot(tt, temp_true, "--", color="k", lw=1.2, label="True temperature")
axs[0].set(ylabel="Temperature (°C)", title="LM35 signal conditioning"); axs[0].legend(loc="upper left", fontsize=9)
axs[1].plot(tt[5:], terr, color=C[0]); axs[1].axhspan(-.5, .5, color=C[2], alpha=.15)
axs[1].set(xlabel="Time (s)", ylabel="Error (°C)", ylim=(-1, 1)); axs[1].text(2, .55, "±0.5 °C", color=C[2], fontsize=9)
for a in axs: a.grid(alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/temperature_conditioning.png", bbox_inches="tight"); plt.close()

# 6) Alert timeline
fig, ax1 = plt.subplots(figsize=(11, 5)); ax2 = ax1.twinx(); ax2.spines["right"].set_visible(True)
ax1.plot(log_t[log_bpm > 0], log_bpm[log_bpm > 0], color=C[0], lw=1.8, label="Heart rate")
ax1.axhline(120, color=C[0], ls="--", lw=1)
ax2.plot(tt, temp_meas, color=C[3], lw=1.8, label="Temperature"); ax2.axhline(38.0, color=C[3], ls="--", lw=1)
for x, a in alerts:
    ax1.axvline(x, color="k", lw=1.2, ls=":")
    ax1.text(x + 1, 142, f"SMS: {AlertManager.NAMES[a].title()}\nt = {x:.0f} s", fontsize=8.5)
ax1.set(xlabel="Time (s)", ylabel="Heart rate (BPM)", ylim=(50, 155), title="Emergency alerts (10 s sustain rule, 5 min cooldown)")
ax2.set(ylabel="Temperature (°C)", ylim=(35.5, 40)); ax1.grid(alpha=.3)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax1.legend(h1 + h2, l1 + l2, loc="lower right")
fig.tight_layout(); fig.savefig(f"{OUT}/alert_timeline.png", bbox_inches="tight"); plt.close()

# 7) Accuracy summary
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
axs[0].hist(err[~near_art], bins=np.arange(-6, 6.25, .25), color=C[0])
axs[0].axvspan(-2, 2, color=C[2], alpha=.12)
axs[0].set(xlabel="BPM error", ylabel="Count", title=f"Heart rate: {np.mean(np.abs(err[~near_art]) <= 2) * 100:.0f}% within ±2 BPM")
axs[1].hist(terr, bins=np.arange(-.8, .82, .04), color=C[3])
axs[1].axvspan(-.5, .5, color=C[2], alpha=.12)
axs[1].set(xlabel="Temperature error (°C)", title=f"Temperature: {np.mean(np.abs(terr) <= .5) * 100:.0f}% within ±0.5 °C")
for a in axs: a.grid(alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/accuracy_summary.png", bbox_inches="tight"); plt.close()

# ---------------------------------------------------------------- summary
print("=== Simulation summary (synthetic signals) ===")
print(f"Beats detected       : {len(det)} of {len(beats)}")
print(f"HR MAE (all)         : {np.mean(np.abs(err)):.2f} BPM, within ±2: {np.mean(np.abs(err) <= 2) * 100:.1f}%")
print(f"HR MAE (no artefacts): {np.mean(np.abs(err[~near_art])):.2f} BPM, within ±2: {np.mean(np.abs(err[~near_art]) <= 2) * 100:.1f}%, max {np.max(np.abs(err[~near_art])):.1f}")
print(f"Temp MAE             : {np.mean(np.abs(terr)):.3f} C, max {np.max(np.abs(terr)):.2f} C, within ±0.5: {np.mean(np.abs(terr) <= .5) * 100:.1f}%")
print(f"5 V single-read MAE  : {np.mean(np.abs(raw5v - temp_true - 0.3)):.3f} C (before calibration offset)")
print("Alerts               :", [(round(x), AlertManager.NAMES[a]) for x, a in alerts])
