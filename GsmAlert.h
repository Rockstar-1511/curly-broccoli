// GsmAlert.h
// Non-blocking SMS sender for a SIM800L GSM module (AT commands over serial).
// Sending is a small state machine so the pulse sampling loop never stalls
// (the MAX30100 FIFO holds only 160 ms of data at 100 sps).

#pragma once
#include <Arduino.h>
#include <SoftwareSerial.h>

class GsmAlert {
public:
    GsmAlert(uint8_t rxPin, uint8_t txPin) : gsm_(rxPin, txPin) {}
    void begin(const char* phoneNumber);
    bool send(const char* message);   // returns false if a message is already in progress
    void poll();                      // call every loop
    bool busy() const { return state_ != IDLE; }

private:
    enum State : uint8_t { IDLE, SET_TEXT_MODE, SET_NUMBER, SEND_BODY, WAIT_DONE };
    void next(State s, uint16_t waitMs);

    SoftwareSerial gsm_;
    const char* number_ = nullptr;
    char msg_[140];
    State state_ = IDLE;
    uint32_t t0_ = 0; uint16_t wait_ = 0;
};
