// config.example.h
// Copy this file to config.h and fill in your values.
// config.h is listed in .gitignore so personal data (phone numbers) is never committed.

#pragma once

// ---- Emergency contact -------------------------------------------------
// International format, e.g. "+15551234567". Kept out of source control.
#define ALERT_PHONE_NUMBER   "+10000000000"

// ---- Alert thresholds --------------------------------------------------
#define HR_LOW_BPM           50      // bradycardia threshold
#define HR_HIGH_BPM          120     // tachycardia threshold
#define TEMP_HIGH_C          38.0f   // fever threshold (after calibration)
#define ALERT_SUSTAIN_MS     10000UL // condition must persist this long
#define ALERT_COOLDOWN_MS    300000UL// minimum time between SMS of the same type

// ---- Sensor calibration ------------------------------------------------
// Offset found by comparing against a reference thermometer.
// LM35 on the skin reads below core temperature, so calibrate in your setup.
#define TEMP_OFFSET_C        0.0f
#define FINGER_THRESHOLD     10000   // raw IR level that indicates a finger is present
#define IR_LED_CURRENT       0x08    // MAX30100 LED_CONFIG IR nibble (0x08 ~ 27 mA)
