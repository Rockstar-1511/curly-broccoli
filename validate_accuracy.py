"""Compare device readings with reference instruments (accuracy validation).

Fill data/validation_readings.csv with paired readings taken at the same
moment, e.g. device vs a clinical pulse oximeter and a digital thermometer.

Usage:  python tools/validate_accuracy.py data/validation_readings.csv
Prints mean error (bias), MAE, max error and 95% limits of agreement, and
saves a Bland-Altman plot for each measurement.
"""
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def analyse(dev, ref, name, unit, tol, ax):
    ok = ~(np.isnan(dev) | np.isnan(ref))
    dev, ref = dev[ok], ref[ok]
    if len(dev) < 2:
        print(f"{name}: not enough paired readings yet")
        return
    diff, mean = dev - ref, (dev + ref) / 2
    bias, sd = diff.mean(), diff.std(ddof=1)
    print(f"{name}: n={len(diff)}, bias={bias:+.2f} {unit}, MAE={np.abs(diff).mean():.2f} {unit}, "
          f"max={np.abs(diff).max():.2f} {unit}, 95% LoA=[{bias - 1.96 * sd:+.2f}, {bias + 1.96 * sd:+.2f}] {unit}, "
          f"within ±{tol}: {np.mean(np.abs(diff) <= tol) * 100:.0f}%")
    ax.scatter(mean, diff)
    ax.axhline(bias, color="k"); ax.axhline(bias + 1.96 * sd, ls="--", color="gray"); ax.axhline(bias - 1.96 * sd, ls="--", color="gray")
    ax.axhspan(-tol, tol, color="green", alpha=.1)
    ax.set(xlabel=f"Mean of device and reference ({unit})", ylabel=f"Device − reference ({unit})", title=f"{name} (Bland-Altman)")
    ax.grid(alpha=.3)


def main(path):
    df = pd.read_csv(path)
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
    analyse(df["device_bpm"].to_numpy(float), df["reference_bpm"].to_numpy(float), "Heart rate", "BPM", 2, axs[0])
    analyse(df["device_temp_c"].to_numpy(float), df["reference_temp_c"].to_numpy(float), "Temperature", "°C", 0.5, axs[1])
    fig.tight_layout()
    out = path.rsplit(".", 1)[0] + "_bland_altman.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")


if __name__ == "__main__":
    main(sys.argv[1])
