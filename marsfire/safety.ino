
/*
 * Check if there is heartbeat.
 */
void checkHeartbeat() {
  // Check if a heartbeat was recently received.
  if (0.001 * (millis() - lastRxdHeartbeat) < MAX_HBEAT_INTERVAL) {
    // Everything is good. No heart beat related error.
    deviceError.num &= ~NOHEARTBEAT;
  } else {
    // No heartbeat received.
    // Setting error flag.
    deviceError.num |= NOHEARTBEAT;
  }
}

/*
 * Check encoder-imu mismatch errors
 */
void checkEncoderIMUMismatch() {
  // If not calibration, there is not error.
  if (calib == NOCALIB) {
    encImuMismatchErrTimer = 0;
    return;
  }
  
  // Calibration has been done.
  bool _noMismatch = abs(theta1 - imuTheta1) < ENC_IMU_MISMATCH_ERR_TH;
  // No mismatch AND no ongoing mismatch error, or there is mismatch AND ongoing error.
  if (_noMismatch)
  {
    encImuMismatchErrTimer = 0;
    return; 
  }

  // Increment timer.
  encImuMismatchErrTimer++;
  // Check of the timer has run out.
  if (enc1ImuMismatchCount * delTime > ENC_IMU_MISMATCH_TIME_TH)
  {
    // Toggle the error flag.
    deviceError.num |= ANG1MISMATCHERR;
    encImuMismatchErrTimer = 0;
  }
}

/*
 * Check encoder1 limits mismatch errors
 */
void checkEncoder1LimitMismatch() {
  // ANG1LIMITERR is not set.
  // If not calibration, there is not error.
  if (calib == NOCALIB) {
    enc1LimitErrTimer = 0;
    return;
  }

  // Calibration has been done.
  bool _limitError = isOutOfLimit(theta1, ANGLE1_MIN_LIMIT, ANGLE1_MAX_LIMIT, DELTA_FOR_ERROR);
  // No limits error AND no ongoing limit error, or there is limit error AND ongoing limit error.
  if (_limitError == false)
  {
    enc1LimitErrTimer = 0;
    return; 
  }
  // Increment timer.
  enc1LimitErrTimer++;
  // Check of the timer has run out.
  if (enc1LimitErrTimer * delTime > ENC_LIM_MISMATCH_TIME_TH)
  {
    // Toggle the error flag.
    deviceError.num |= ANG1LIMITERR;
    enc1LimitErrTimer = 0;
  }
}

/*
 * Check encoder234 limits mismatch errors
 */
void checkEncoder234LimitMismatch() {
  // ANG234LIMITERR is not set.
  // If not calibration, there is not error.
  if (calib == NOCALIB) {
    enc234LimitErrTimer = 0;
    return;
  }
  
  // Calibration has been done.
  bool _limitError = (isOutOfLimit(theta2, ANGLE2_MIN_LIMIT, ANGLE2_MAX_LIMIT, DELTA_FOR_ERROR)
                      || isOutOfLimit(theta3, ANGLE3_MIN_LIMIT, ANGLE3_MAX_LIMIT, DELTA_FOR_ERROR)
                      || isOutOfLimit(theta4, ANGLE4_MIN_LIMIT, ANGLE4_MAX_LIMIT, DELTA_FOR_ERROR));
  // No limits error AND no ongoing limit error, or there is limit error AND ongoing limit error.
  if (_limitError == false)
  {
    enc234LimitErrTimer = 0;
    return; 
  }
  // Increment timer.
  enc234LimitErrTimer++;
  // Check of the timer has run out.
  if (enc234LimitErrTimer * delTime > ENC_LIM_MISMATCH_TIME_TH)
  {
    // Toggle the error flag.
    deviceError.num |= ANG234LIMITERR;
    enc234LimitErrTimer = 0;
  }
}

/*
 * Check angle jump errors
 */
void checkEncoderJump() {
  if (calib == NOCALIB) return;

  // Angle sensor 1 jump
  if (abs(theta1 - theta1Prev) >= ANG_JUMP_ERROR) {
    deviceError.num |= ANG1JUMPERR;
  }
}

/*
 * Handles errors
 */
void handleErrors() {
  // If error enable motor control and move on.
  if (deviceError.num == 0) 
  {
    digitalWrite(SAFETY_PIN, HIGH);
    return;
  }
  // Check if its angle related error.
  setControlType(NONE);
  if ((deviceError.num == ANG1MISMATCHERR)
      || (deviceError.num == ANG234MISMATCHERR)
      || (deviceError.num == ANG1JUMPERR)
      || (deviceError.num == ANG234JUMPERR)) 
  {
    // There is angle realted error.
    setLimb(NOLIMB);
    calib = NOCALIB;
  }
  // Switching off the motor for safety.
  digitalWrite(SAFETY_PIN, LOW);
}
