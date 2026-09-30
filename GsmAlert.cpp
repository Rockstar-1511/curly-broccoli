// GsmAlert.cpp
#include "GsmAlert.h"

void GsmAlert::begin(const char* phoneNumber) {
    number_ = phoneNumber;
    gsm_.begin(9600);
    gsm_.println(F("AT"));
}

bool GsmAlert::send(const char* message) {
    if (state_ != IDLE) return false;
    strncpy(msg_, message, sizeof(msg_) - 1);
    msg_[sizeof(msg_) - 1] = '\0';
    next(SET_TEXT_MODE, 0);
    return true;
}

void GsmAlert::next(State s, uint16_t waitMs) {
    state_ = s; t0_ = millis(); wait_ = waitMs;
}

void GsmAlert::poll() {
    while (gsm_.available()) gsm_.read();     // discard module responses
    if (state_ == IDLE || millis() - t0_ < wait_) return;

    switch (state_) {
        case SET_TEXT_MODE:
            gsm_.println(F("AT+CMGF=1"));     // SMS text mode
            next(SET_NUMBER, 300);
            break;
        case SET_NUMBER:
            gsm_.print(F("AT+CMGS=\""));
            gsm_.print(number_);
            gsm_.println(F("\""));
            next(SEND_BODY, 300);
            break;
        case SEND_BODY:
            gsm_.print(msg_);
            gsm_.write(26);                   // Ctrl+Z ends the message
            next(WAIT_DONE, 5000);            // module needs a few seconds to send
            break;
        case WAIT_DONE:
            next(IDLE, 0);
            break;
        default:
            state_ = IDLE;
    }
}
