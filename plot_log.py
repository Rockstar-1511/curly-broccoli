"""Plot a logged monitoring session (heart rate, temperature, alerts).

Usage:  python tools/plot_log.py data/session.csv
"""
import sys

import matplotlib.pyplot as plt
import pandas as pd

ALERTS = {1: "Low HR", 2: "High HR", 3: "High temp"}


def main(path):
    df = pd.read_csv(path)
    t = (df["time_ms"] - df["time_ms"].iloc[0]) / 1000
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    hr = df["bpm"].where(df["bpm"] > 0)
    a1.plot(t, hr, lw=1.6); a1.set_ylabel("Heart rate (BPM)"); a1.grid(alpha=.3)
    a2.plot(t, df["temp_c"], color="#C44E52", lw=1.6); a2.set_ylabel("Temperature (°C)")
    a2.set_xlabel("Time (s)"); a2.grid(alpha=.3)
    for ti, a in zip(t[df["alert"] > 0], df["alert"][df["alert"] > 0]):
        for ax in (a1, a2):
            ax.axvline(ti, color="k", ls=":")
        a1.text(ti, a1.get_ylim()[1], ALERTS.get(int(a), "alert"), fontsize=8, va="top")
    a1.set_title(f"Monitoring session: {path}")
    fig.tight_layout()
    out = path.rsplit(".", 1)[0] + ".png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")


if __name__ == "__main__":
    main(sys.argv[1])
