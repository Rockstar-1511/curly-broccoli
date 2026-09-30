"""Check that the Python pipeline matches the firmware C++ PulseProcessor.

Usage (from this folder):
    python ../simulation/synthetic_signals.py          # writes ppg_input.csv
    g++ -O2 -I../firmware/health_monitor test_pulse.cpp \
        ../firmware/health_monitor/PulseProcessor.cpp \
        ../firmware/health_monitor/AlertManager.cpp -o test_pulse
    ./test_pulse ppg_input.csv > cpp_out.csv
    python compare_with_firmware.py ppg_input.csv cpp_out.csv
"""
import sys
import numpy as np

sys.path.insert(0, "../simulation")
from pulse_pipeline import PulseProcessor  # noqa: E402


def main(ppg_csv, cpp_csv):
    ppg = np.loadtxt(ppg_csv, delimiter=",", skiprows=1, dtype=np.int64)
    cpp = np.genfromtxt(cpp_csv, delimiter=",", names=True)

    p = PulseProcessor()
    py_bpm, next_log = [], 1000
    for t_ms, ir in ppg:
        p.update(int(ir), int(t_ms))
        if t_ms >= next_log:
            py_bpm.append(p.bpm if p.finger and p.bpm > 0 else 0.0)
            next_log += 1000

    py_bpm = np.array(py_bpm)
    n = min(len(py_bpm), len(cpp))
    diff = np.abs(py_bpm[:n] - cpp["bpm"][:n])
    print(f"Compared {n} one-second outputs, max difference {diff.max():.3f} BPM")
    # float32 (firmware) vs float64 (Python) rounding allows a small difference
    if diff.max() > 0.5:
        sys.exit("FAIL: Python pipeline and firmware disagree")
    print("PASS")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
