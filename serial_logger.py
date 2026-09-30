"""Log the monitor's serial CSV output to a file with PC timestamps.

Usage:  python tools/serial_logger.py --port COM3 --out data/session.csv
        python tools/serial_logger.py --port /dev/ttyUSB0
Requires: pip install pyserial
"""
import argparse
import datetime as dt
import sys

import serial  # pyserial


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", required=True, help="serial port, e.g. COM3 or /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--out", default=f"data/session_{dt.datetime.now():%Y%m%d_%H%M%S}.csv")
    args = ap.parse_args()

    with serial.Serial(args.port, args.baud, timeout=2) as ser, open(args.out, "w", encoding="utf-8") as f:
        f.write("pc_time,time_ms,bpm,temp_c,finger,alert\n")
        print(f"Logging {args.port} -> {args.out} (Ctrl+C to stop)")
        try:
            while True:
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if not line or line.startswith(("#", "time_ms")):
                    if line.startswith("#"):
                        print(line)          # device status messages
                    continue
                if line.count(",") != 4:
                    continue                 # skip partial lines
                f.write(f"{dt.datetime.now().isoformat(timespec='seconds')},{line}\n")
                f.flush()
                print(line)
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
