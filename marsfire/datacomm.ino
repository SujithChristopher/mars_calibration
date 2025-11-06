
//#define SerialPort SerialUSB
//#include "variable.h"
//#include "CustomDS.h"


// Read and handle incoming messages.
// Many commands will be ignored if there is a device error.
void readHandleIncomingMessage() {
  byte _cmdSet = 0x00;
  byte _details;
  int plSz = serReader.readUpdate();

  // Read handle incoming data
  if (plSz > 0) {
    _details = serReader.payload[1];
    // Handle new message.
    // Check the command type.
    // if (serReader.payload[0] != 0x80) SerialUSB.println(serReader.payload[0]);
    switch (serReader.payload[0]) {
      case START_STREAM:
        stream = true;
        streamType = SENSORSTREAM;
        _cmdSet = 0x01;
        break;
      case STOP_STREAM:
        stream = false;
        _cmdSet = 0x01;
        break;
      case SET_DIAGNOSTICS:
        stream = true;
        streamType = DIAGNOSTICS;
        _cmdSet = 0x01;
        break;
      case SET_CONTROL_TYPE:
        // This can be set only if there is not error.
        if (deviceError.num != 0) break;
        // Device must be calibration.
        if (calib == NOCALIB) break;
        // Limb has to be set.
        if (currLimb == NOLIMB) break;
        // This command can be used only if the current control mode is NONE.
        // Set control.
        _cmdSet = setControlType(_details) ? 0x01 : 0x00;
        break;
      case SET_CONTROL_TARGET:
        // No control target setting for NONE.
        if (ctrlType == NONE) break;
        // Make sure that a minimum amount of time has passed since the previous target set.
        if ((runTime.num - targetSetTime) < TARGET_SET_BACKOUT) break;
        // This can be set only if there is not error.
        if (deviceError.num != 0) break;
        // Ensure that the position is not changing too rapidly.
        // This can lead to oscillations.
        if (abs(omega1) > POSITION_RATE_LIMIT) break;
        // All preliminary checks are done.
        // Parse the target details.
        parseTargetDetails(serReader.payload, 1, tempArray);
        // Check that the target is within the appropriate limits.
        // tempArray[2] has the target value.
        if ((ctrlType == POSITION) && 
            (isWithinRange(tempArray[2], POSITION_TARGET_MIN, POSITION_TARGET_MAX) == false)) break;
        // Set target.
        // Choose the initial value.
        strtPos = tempArray[0];
        // Set the rest of the target related variables.
        strtTime = tempArray[1];
        target = tempArray[2];
        tgtDur = tempArray[3];        
        // Initial time.
        initTime = runTime.num / 1000.0f + strtTime;
        // Set the current target set time.
        targetSetTime = runTime.num;
        _cmdSet = 0x01;
        break;
      case SET_LIMB:
        // Set the limb to NOLIMB by default.
        setLimb(NOLIMB); 
        // This can only be set if there is no error.
        if (deviceError.num != 0) break;
        // This can only be set if the control is NONE.
        if (ctrlType != NONE) break;
        // Reset calibration
        calib = NOCALIB;
        // Make sure the input limb is one of the valid options.
        setLimb(isValidLimb(_details) ? _details : NOLIMB);
        _cmdSet = 0x01;
        break;
      case CALIBRATE:
        // This can be set only if there is no error.
        if (deviceError.num != 0) break;
        // This can only eb set if the control is NONE.
        if (ctrlType != NONE) break;
        // Check if the limb has been set.
        if (currLimb == NOLIMB) break;
        // Reset calibration
        // Check the calibration value
        calib = NOCALIB;
        // Ensure that the IMU angles are not too off.
        if ((imuTheta1 < CALIB_IMU_ANGLE_MIN) || 
            (imuTheta2 < CALIB_IMU_ANGLE_MIN) || 
            (imuTheta3 < CALIB_IMU_ANGLE_MIN) || 
            (imuTheta4 < CALIB_IMU_ANGLE_MIN) || 
            (imuTheta1 > CALIB_IMU_ANGLE_MAX) || 
            (imuTheta2 > CALIB_IMU_ANGLE_MAX) || 
            (imuTheta3 > CALIB_IMU_ANGLE_MAX) || 
            (imuTheta4 > CALIB_IMU_ANGLE_MAX)) break;
        // Set the offset angles.
        theta1Offset = currLimb == RIGHT ? imuTheta1 : -imuTheta1;
        theta2Offset = currLimb == RIGHT ? imuTheta2 : -imuTheta2;;
        theta3Offset = currLimb == RIGHT ? imuTheta3 : -imuTheta3;;
        theta4Offset = imuTheta4;
        // Reset encoder counts.
        angle1.write(0);
        angle2.write(0);
        angle3.write(0);
        angle4.write(0);
        // Reset previous angles to 0.
        theta1 = limbAngleScale * theta1Offset;
        theta1Prev = theta1; // This to avoid triggering ANG1JUMPERR 
        theta2 = limbAngleScale * theta2Offset;
        theta3 = limbAngleScale * theta3Offset;
        theta4 = limbAngleScale * (-theta4Offset);
        calib = YESCALIB;
        _cmdSet = 0x01;
        break;
      case GET_VERSION:
        stream = false;
        // Send the current firmware version.
        sendVersionDetails();
        _cmdSet = 0x02;
        break;
      case HEARTBEAT:
        lastRxdHeartbeat = millis();
        _cmdSet = 0x02;
        break;
      case RESET_PACKETNO:
        packetNumber.num = 0;
        startTime = millis();
        runTime.num = 0;
        _cmdSet = 0x01;
        break;
    }
    // Update command status
    if (_cmdSet != 0x02) {
      cmdStatus = (_cmdSet == 0x01) ? COMMAND_SUCCESS : COMMAND_FAIL;
    }
    serReader.payloadHandled();
  }
}

void writeSensorStream()
{
  // Format:
  // 255 | 255 | No. of bytes | Status | Error Val 1 | Error Val 2 | ...
  // Payload | Chksum
  byte header[] = {0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00 };
  byte chksum = 0xFE;
  byte _temp;

  //Out data buffer
  outPayload.newPacket();
  outPayload.add(theta1);
  outPayload.add(theta2);
  outPayload.add(theta3);
  outPayload.add(theta4);
  outPayload.add(imuTheta1);
  outPayload.add(imuTheta2);
  outPayload.add(imuTheta3);
  outPayload.add(imuTheta4);
  outPayload.add(epForce);
  outPayload.add(target);
  outPayload.add(desired.val(0));
  outPayload.add(control.val(0));

  // Add additional data if in DIAGNOSTICS mode
  if (streamType == DIAGNOSTICS) {
    outPayload.add(err);
    outPayload.add(errdiff);
    outPayload.add(errsum);
    outPayload.add(marsGCTorque);
    outPayload.add(omega1);
  }

  // Send packet.
  header[2] = (4                      // Four headers
               + 2                    // Packet number int16
               + 4                    // Run time
               + outPayload.sz() * 4  // Float sensor data
               + 1                    // Checksum
               );
  header[3] = getProgramStatus(streamType);
  header[4] = deviceError.bytes[0];
  header[5] = deviceError.bytes[1];
  header[6] = getAdditionalInfo();
  chksum += header[2] + header[3] + header[4] + header[5] + header[6];

  //Send header
  bt.write(header[0]);
  bt.write(header[1]);
  bt.write(header[2]);
  bt.write(header[3]);
  bt.write(header[4]);
  bt.write(header[5]);
  bt.write(header[6]);
  
  // Send packet number
  for (int i = 0; i < 2; i++) {
    bt.write(packetNumber.bytes[i]);
    chksum += packetNumber.bytes[i];
  }

  // Send current run time
  for (int i = 0; i < 4; i++) {
    bt.write(runTime.bytes[i]);
    chksum += runTime.bytes[i];
  }

  // Send the floats
  for (int i = 0; i < outPayload.sz() * 4; i++) {
    _temp = outPayload.getByte(i);
    bt.write(_temp);
    chksum += _temp;
  }
  
  bt.write(chksum);
  bt.flush();
}


void sendVersionDetails() {
  // Format:
  // 255 | 255 | No. of bytes | Status | Error Val 1 | Error Val 2 | ...
  // [Current Mechanism][isActuated] | Payload | Chksum
  byte header[] = { 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00 };
  byte chksum = 0xFE;

  // Send packet.
  header[2] = (4                      // Four headers
               + strlen(fwVersion)    // Version string length
               + 1                    // Comma separator
               + strlen(deviceId)     // Deviice ID string length
               + 1                    // Comma separator
               + strlen(compileDate)  // Compilation date.
               + 1                    // Checksum
  );
  header[3] = getProgramStatus(VERSION);
  header[4] = deviceError.bytes[0];
  header[5] = deviceError.bytes[1];
  header[6] = getAdditionalInfo();
  chksum += header[2] + header[3] + header[4] + header[5] + header[6];

  // Send the header.
  bt.write(header[0]);
  bt.write(header[1]);
  bt.write(header[2]);
  bt.write(header[3]);
  bt.write(header[4]);
  bt.write(header[5]);
  bt.write(header[6]);

  // Send Device ID
  for (unsigned int i = 0; i < strlen(deviceId); i++) {
    bt.write(deviceId[i]);
    chksum += deviceId[i];
  }
  bt.write(',');
  chksum += ',';
  // Send firmware version
  for (unsigned int i = 0; i < strlen(fwVersion); i++) {
    bt.write(fwVersion[i]);
    chksum += fwVersion[i];
  }
  bt.write(',');
  chksum += ',';
  // Send firmware compilation date
  for (unsigned int i = 0; i < strlen(compileDate); i++) {
    bt.write(compileDate[i]);
    chksum += compileDate[i];
  }
  // Send Checksum
  bt.write(chksum);
  bt.flush();
}

/*
 * Check if the given limb is valid.
 */
bool isValidLimb(byte limbval) {
  return (
    (limbval == NOLIMB) ||
    (limbval == RIGHT) ||
    (limbval == LEFT)
  );
}

// Parse the toque/position target details.
void parseTargetDetails(byte* payload, int strtInx, float *out) {
  int inx = strtInx;
  floatunion_t temp;
  // The are four floats: start position, start time, target, duration.
  // Initial position
  _assignFloatUnionBytes(inx, payload, &temp);
  out[0] = temp.num;
  // Initial time
  inx += 4;
  _assignFloatUnionBytes(inx, payload, &temp);
  out[1] = min(0, temp.num);
  // Target
  inx += 4;
  _assignFloatUnionBytes(inx, payload, &temp);
  out[2] = temp.num;
  // Duration
  inx += 4;
  _assignFloatUnionBytes(inx, payload, &temp);
  out[3] = max(MIN_TARGET_DUR, temp.num);
}

// Handle the SerialUSB commands.
void handleSerialUSBCommands()
{
  if (SerialUSB.available()) {
    if (SerialUSB.read() == '1')
    {
      SerialUSB.print("MARS - ");
      SerialUSB.print(fwVersion);
      SerialUSB.print(" | ");
      SerialUSB.print(deviceId);
      SerialUSB.print(" | ");
      SerialUSB.println(compileDate);
    }
  }
}
