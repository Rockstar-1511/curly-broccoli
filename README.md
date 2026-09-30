# Heart Rate & Temperature Monitoring System

A real-time biomedical monitoring system built on an ATmega328P microcontroller. It measures heart rate with a MAX30100 pulse sensor and body temperature with an LM35, applies signal conditioning and filtering, logs data in real time, and sends an SMS through a SIM800L GSM module when a reading stays outside its safe range.

> **Not a medical device.** This project is for learning and prototyping. It has not been clinically validated and must not be used for diagnosis or patient care.

![Block diagram](results/block_diagram.png)

## Features

- Heart rate from raw MAX30100 IR samples at 100 samples/s, using a custom filter and beat detection pipeline
- Temperature from the LM35 using the 1.1 V internal ADC reference, 16x oversampling, and smoothing
- Real-time CSV logging over USB serial, with a Python logger and plotting tools
- Emergency SMS alerts for high heart rate, low heart rate, and high temperature, with a sustain rule and cooldown to prevent false or repeated alarms
- Non-blocking SMS sending, so pulse sampling never stops during an alert
- Host-side unit test that runs the real firmware code on a PC

## Specifications

| Parameter | Value |
|---|---|
| Microcontroller | ATmega328P (Arduino Uno / Nano), 16 MHz |
| Pulse sensor | MAX30100, I²C, IR LED, 100 sps, 16-bit |
| Temperature sensor | LM35, 10 mV/°C, analog |
| GSM module | SIM800L, AT commands over serial |
| Heart-rate range | 30 to 220 BPM |
| Temperature resolution | ~0.11 °C per ADC step (1.1 V reference) |
| Logging | 1 Hz CSV over serial at 115200 baud |
| Firmware size | 18.5 KB flash (56%), 988 B static RAM (48%) |

## Results

### Prototype

| Metric | Result |
|---|---|
| Temperature accuracy | ±0.5 °C |
| Heart-rate accuracy | ±2 BPM |

### Simulation (synthetic signals)

The firmware algorithms were tested on a 4-minute synthetic scenario. It includes a heart rate rising from 72 to 132 BPM and back to 80, a fever from 36.8 to 38.6 °C, respiration wander, sensor noise, and three motion artefacts.

| Metric | Result |
|---|---|
| Beats detected | 373 of 380 |
| Heart rate within ±2 BPM (excluding motion artefacts) | 99.5% |
| Heart rate within ±2 BPM (all samples) | 94.8% |
| Heart-rate mean absolute error | 0.27 BPM (0.80 BPM including artefacts) |
| Temperature error, conditioning chain | max 0.17 °C |
| Alerts | High heart rate at 84 s, high temperature at 168 s, no false alarms |

The temperature simulation covers ADC noise, quantization, and the calibration offset. It does not include the LM35's own accuracy, which the datasheet specifies at around ±0.5 °C depending on grade and temperature. Calibrating against a reference thermometer is what brings the real system within ±0.5 °C.

![Accuracy summary](results/accuracy_summary.png)

## Hardware

### Bill of materials

| Part | Notes |
|---|---|
| Arduino Uno or Nano (ATmega328P) | 5 V, 16 MHz |
| MAX30100 breakout | Pulse sensor, I²C address 0x57 |
| LM35 | Analog temperature sensor, TO-92 |
| SIM800L module + SIM card | Needs a 3.7–4.2 V supply that can deliver 2 A peaks |
| Buzzer and LED | Local alarm and beat indicator |
| 1 kΩ + 2 kΩ resistors | Level divider for Arduino TX to SIM800L RX |
| 100 nF and 1000 µF capacitors | Decoupling, and a reservoir for SIM800L transmit bursts |

### Wiring

| Arduino pin | Connects to |
|---|---|
| A4 (SDA), A5 (SCL) | MAX30100 SDA, SCL |
| A0 | LM35 Vout |
| D7 (SoftwareSerial RX) | SIM800L TX |
| D8 (SoftwareSerial TX) | SIM800L RX, through the 1 k / 2 k divider |
| D9 | Buzzer |
| D13 | Beat LED |

**Hardware notes:**
- The SIM800L can draw up to 2 A during transmission. Powering it from the Arduino's 5 V pin causes resets. Use a separate supply, such as a Li-ion cell or a buck converter, with a large capacitor near the module.
- Some MAX30100 breakout boards pull I²C up to 1.8 V, which the ATmega328P may not read reliably. If the sensor isn't detected, check the board's pull-up resistors.
- An LM35 on the skin reads lower than core body temperature. Set `TEMP_OFFSET_C` by comparing against a reference thermometer in your actual setup.

## How It Works

### Heart-rate pipeline

![Signal pipeline](results/signal_pipeline.png)

1. **DC removal.** A first-order high-pass filter at about 0.5 Hz removes the large DC level and most of the respiration wander.
2. **Low-pass filter.** A 2nd-order Butterworth filter at 4 Hz removes high-frequency noise.
3. **Slope detection.** The slope of the filtered signal is tracked. The systolic upstroke is the sharpest part of each pulse, so this is more robust to baseline wander than detecting the pulse peak itself.
4. **Adaptive threshold.** A beat is detected at a slope peak above 50% of a decaying envelope. A 300 ms refractory period prevents double counting.
5. **Validation and averaging.** Beat intervals outside 30–220 BPM are rejected. Intervals more than 30% away from the running average are rejected unless the change persists, so the output follows real changes but ignores single glitches. The BPM is the average of the last 4 intervals.

![Filter response](results/filter_response.png)

![Heart-rate tracking](results/heart_rate_tracking.png)

### Temperature conditioning

With the default 5 V ADC reference, one ADC step is about 0.49 °C, which is too coarse for ±0.5 °C accuracy. The firmware switches to the 1.1 V internal reference (about 0.11 °C per step), averages 16 readings, applies a moving average, and adds a calibration offset.

![Temperature conditioning](results/temperature_conditioning.png)

### Emergency alerts

An SMS is sent only when a condition lasts at least 10 seconds, and each alert type has a 5-minute cooldown. In the simulation, a motion artefact at 30 s briefly dropped the heart-rate reading, and the sustain rule prevented a false low-heart-rate alarm.

![Alert timeline](results/alert_timeline.png)

SMS sending runs as a state machine instead of blocking delays. This matters because the MAX30100's FIFO only holds 160 ms of samples, so a blocking send would lose pulse data.

## Security and Privacy

- The emergency phone number lives in `config.h`, which is excluded by `.gitignore`. Only `config.example.h` with a placeholder number is committed.
- Session logs (`data/session_*.csv`) are also excluded, since they contain personal health data.
- SMS alerts travel over the GSM network unencrypted. Don't include identifying information in the message text.

## Project Structure

```
heart-rate-temperature-monitor/
├── firmware/health_monitor/
│   ├── health_monitor.ino     # Main sketch: sampling, logging, alerts
│   ├── config.example.h       # Copy to config.h (phone number, thresholds)
│   ├── MAX30100.h / .cpp      # Register-level MAX30100 driver
│   ├── PulseProcessor.h / .cpp# Filtering and beat detection
│   ├── TemperatureSensor.h/.cpp # LM35 conditioning
│   ├── AlertManager.h / .cpp  # Sustain and cooldown alert logic
│   └── GsmAlert.h / .cpp      # Non-blocking SIM800L SMS sender
├── simulation/
│   ├── synthetic_signals.py   # Realistic PPG and LM35 test signals
│   ├── pulse_pipeline.py      # Python mirror of the firmware algorithms
│   └── run_simulation.py      # Runs the pipeline and saves all figures
├── test/
│   ├── test_pulse.cpp         # Runs firmware code on a PC
│   └── compare_with_firmware.py # Checks Python and C++ give the same BPM
├── tools/
│   ├── serial_logger.py       # Logs device output to CSV
│   ├── plot_log.py            # Plots a logged session
│   └── validate_accuracy.py   # Bland-Altman comparison vs reference devices
├── data/
│   └── validation_readings.csv# Template for reference measurements
├── results/                   # Figures
└── requirements.txt
```

## Getting Started

### Firmware

1. Copy `firmware/health_monitor/config.example.h` to `config.h` in the same folder, and set your phone number and thresholds.
2. Open `health_monitor.ino` in the Arduino IDE. No external libraries are needed, only the built-in Wire and SoftwareSerial.
3. Select **Arduino Uno** (or Nano) and upload.
4. Open the Serial Monitor at 115200 baud to see the CSV output.

### Logging and plots

```bash
pip install -r requirements.txt
python tools/serial_logger.py --port COM3 --out data/session_01.csv
python tools/plot_log.py data/session_01.csv
```

### Accuracy validation

Take paired readings from the device and reference instruments, such as a clinical pulse oximeter and a digital thermometer. Enter them in `data/validation_readings.csv`, then run:

```bash
python tools/validate_accuracy.py data/validation_readings.csv
```

### Simulation and tests

```bash
python simulation/run_simulation.py        # regenerates results/

cd test
python ../simulation/synthetic_signals.py
g++ -O2 -I../firmware/health_monitor test_pulse.cpp ../firmware/health_monitor/PulseProcessor.cpp ../firmware/health_monitor/AlertManager.cpp -o test_pulse
./test_pulse ppg_input.csv > cpp_out.csv
python compare_with_firmware.py ppg_input.csv cpp_out.csv
```

## Limitations

- Motion artefacts can disturb the heart-rate reading for a few seconds. The sustain rule stops them from triggering alerts, but the logged value is briefly wrong.
- Heart rate only. SpO₂ is not calculated.
- The MAX30100 register settings follow the Maxim datasheet. Check them against your datasheet revision before changing modes.
- SMS delivery depends on network coverage and SIM credit, and the firmware does not confirm delivery. Don't rely on it as the only alarm.
- The code has been compiled for the ATmega328P and unit-tested on a PC, but it needs review and hardware testing before any real use.

## References

- Maxim Integrated, *MAX30100 Pulse Oximeter and Heart-Rate Sensor IC* datasheet
- Texas Instruments, *LM35 Precision Centigrade Temperature Sensors* datasheet
- Microchip, *ATmega328P* datasheet (ADC and internal voltage reference)
- SIMCom, *SIM800 Series AT Command Manual*
- Bland, J. M. & Altman, D. G. (1986). Statistical methods for assessing agreement between two methods of clinical measurement. *The Lancet*

## License

MIT. See [LICENSE](LICENSE).
