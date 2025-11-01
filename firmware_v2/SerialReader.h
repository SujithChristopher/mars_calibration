
#ifndef SerialReader_h
#define SerialReader_h

#include "Arduino.h"

#define INCOMING_HEADER_BYTE  0xAA

enum ReaderState {
  WAITFORPACKET,
  HEADER1,
  HEADER2,
  PAYLOAD,
  CHKSUM,
  WAITFORHANDLING
 
};

class SerialReader {
  public:
    static const byte maxPayloadSize = 255;
    bool temp = false;
    byte payload[maxPayloadSize];
    SerialReader();
    int readUpdate();
    void payloadHandled();
  private:
 
 // Serial communciation related dataa
    byte _currByte;
    unsigned int _currPlSz;
    unsigned int _plCntr;
    byte _chksum;
    ReaderState _state;
};



#endif
