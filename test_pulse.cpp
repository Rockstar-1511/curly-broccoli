// Host unit test: runs the firmware PulseProcessor and AlertManager on a
// recorded or synthetic IR signal (CSV: time_ms,ir) and prints BPM once per
// second. Build (from this folder):
//   g++ -O2 -I../firmware/health_monitor test_pulse.cpp ../firmware/health_monitor/PulseProcessor.cpp ../firmware/health_monitor/AlertManager.cpp -o test_pulse
#include <cstdio>
#include <cstdlib>
#include "PulseProcessor.h"
#include "AlertManager.h"

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage: test_pulse ppg.csv\n"); return 1; }
    FILE* f = std::fopen(argv[1], "r");
    if (!f) { std::perror("open"); return 1; }

    PulseProcessor pulse; pulse.begin(100.0f, 4.0f, 10000);
    AlertManager alerts;  alerts.begin(50, 120, 38.0f, 10000, 300000);

    char line[64];
    if (!std::fgets(line, sizeof line, f)) return 1;   // header
    unsigned long t; unsigned ir; unsigned long nextLog = 1000; int beats = 0;
    std::printf("time_ms,bpm,alert\n");
    while (std::fscanf(f, "%lu,%u", &t, &ir) == 2) {
        if (pulse.update((uint16_t)ir, (uint32_t)t)) beats++;
        if (t >= nextLog) {
            const bool valid = pulse.fingerPresent() && pulse.bpm() > 0;
            AlertType a = alerts.evaluate(pulse.bpm(), valid, 36.8f, (uint32_t)t);
            std::printf("%lu,%.2f,%d\n", t, valid ? pulse.bpm() : 0.0f, (int)a);
            nextLog += 1000;
        }
    }
    std::fclose(f);
    std::fprintf(stderr, "beats detected: %d\n", beats);
    return 0;
}
