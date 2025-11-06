/* Functions to implement the different controllers for the 
 *  MARS robot.
 *  
 *  Author: Sivakumar Balasubramanian.
 *  Date: 01 July 2025
 */


// Changing control types must always be done by calling this function.
// This will ensure all the control related variables are set correctly.
// This function will allow us to set a new control type only from the NONE
// control type. It does not allow transition between control modes.
bool setControlType(byte ctype) {
  // We want to change the current control type to NONE. No problem. Just
  // change it and leave.
  if (ctype == NONE) {
    ctrlType = NONE;
    target = INVALID_TARGET;
    desired.add(INVALID_TARGET);
    return true;
  }
  // We want to set some other control mode. This can be done only if the 
  // current control mode is NONE.
  // Leave if the current control type is not NONE.
  if (ctrlType != NONE) return false;
  // Alright, the current control model is NONE.
  switch (ctype) {
    case POSITION:
      // Nothing needs to be set.
      ctrlType = ctype;
      break;
  }
  target = INVALID_TARGET;
  desired.add(INVALID_TARGET);
  return true;
}

void updateControlLaw() {
  float _currI = 0.0;
  float _currPWM = 0.0;
  float _prevPWM = control.val(0);
  bool _motorEnabled = true;
  // Else we need to take the appropriate action.
  switch (ctrlType) {
    case NONE:
      // Check control can be disabled.
      if (_prevPWM == 0) {
        digitalWrite(MOTOR_ENABLE, LOW);
        _motorEnabled = false;
      }
      // Keep the control buffers clean.
      err = 0.0;
      errdiff = 0.0;
      errsum = 0.0;
      control.add(0.0);
      break;
    case POSITION:
      // Update desired position
      desired.add(getDesiredPositionValue());
      // MARS gravity compensation torque
      marsGCTorque = MARS_GRAV_COMP_ADJUST * limbControlScale * getMarsGravityCompensationTorque() / MOTOR_T2I;
      _currI = marsGCTorque;
      // Position control.
      _currI += limbControlScale * controlPosition();
      _currPWM = convertCurrentToPWM(_currI);
      break;
  }
  // Dampen control.
  _currPWM = dampenControlForSafety(_currPWM, ctrlType, currLimb);
  // Clip PWM value
  _currPWM = min(MAXPWM, max(-MAXPWM, _currPWM));
  // Send PWM value to motor controller & update control.
  if (_motorEnabled) {
    sendPWMToMotor(_currPWM);
  }
  control.add(_currPWM);
}

// Position controller
float controlPosition() {
  float _currang = actual.val(0);
  float _currtgt = desired.val(0);
  float _prevang = actual.val(1);
  float _prevtgt = desired.val(1);
  float _currp, _currd, _curri;
  float _currerr, _preverr, _currderr;
  float _errsum = errsum;
  
  // Check if position control is disabled, or we should have valid 
  // current and previous desired positions. 
  if ((_currtgt == INVALID_TARGET) || (_prevtgt == INVALID_TARGET)) {
    err = 0.0;
    errdiff = 0.0;
    errsum = 0.0;
    return 0.0;
  }

  // Update error related information.
  // Current error: Limit the error to be between +/- POS_ERROR_DIFF_LIMIT
  // _currerr = min(POS_ERROR_DIFF_LIMIT, max(-POS_ERROR_DIFF_LIMIT, _currtgt - _currang));
  _currerr = _currtgt - _currang;
  // Ignore small errors.
  _currerr = (abs((_currerr)) <= POS_CTRL_DBAND) ? 0.0 : _currerr;
  // Proportional control term.
  _currp = pcKp * (_currerr);

  // Previous error: Limit the error to be between +/- POS_ERROR_DIFF_LIMIT
  _preverr = (_prevtgt != INVALID_TARGET) ? _prevtgt - _prevang : _currerr;
  // Derivate control term.
  _currderr = _currerr - _preverr;
  _currd = pcKd * _currderr;

  // Error sum.
  if (pcKi == 0) _curri = 0;
  else {
    _errsum = 0.9999 * _errsum + _currerr;
    float _intlim = INTEGRATOR_LIMIT / pcKi;
    _errsum = min(_intlim, max(-_intlim, _errsum));
    // Integral control term.
    _curri = pcKi * _errsum;
  }

  // Log error information
  err = _currp;
  errdiff = _currd;
  errsum = _currp + _currd;

  // Error based scaling of control output.
  // Have different fall and rise times.
  if (getControlScaleForScaledError(_currerr / POS_ERROR_DIFF_LIMIT) < ctrlScale) {
    ctrlScale = 0.9 * ctrlScale + 0.1 * getControlScaleForScaledError(_currerr / POS_ERROR_DIFF_LIMIT);
  } else {
    ctrlScale = 0.97 * ctrlScale + 0.03 * getControlScaleForScaledError(_currerr / POS_ERROR_DIFF_LIMIT);
  }
  ctrlScale = max(0, min(1, ctrlScale));
  return ctrlScale * (_currp + _currd + _curri);
}


// Bound the position control output.
float boundPositionControl(float pwm_value) {
  if (pwm_value > MAXPWM) {
    return MAXPWM;
  } else if (pwm_value < -MAXPWM) {
    return -MAXPWM;
  }
  return pwm_value;
}

// Rate limit a variable.
float rateLimitValue(float curr, float prev, float rlim) {
  float _del = curr - prev;
  if (_del >= rlim) {
    return prev + rlim;
  } else if (_del <= -rlim) {
    return prev - rlim;
  }
  return curr;
}

// Dampen the control output if the speed is too fast.
float dampenControlForSafety(float currPWM, byte cType, byte currLimb) {
  float _bDamp = 0.0;
  float _sign = omega1 > 0 ? +1 : -1;
  float _vel;
  // Check of no limb is set. If so, then damn both ways.
  if (currLimb == NOLIMB) {
    _bDamp = SAFETY_DAMP_VALUE;
    _vel = omega1 / 5.0;
  } else {
    switch(ctrlType) {
      case NONE:
        _bDamp = omega1 > 0 ? SAFETY_DAMP_VALUE : 0.0;
        _vel = omega1 / 5.0;
        break;
      case POSITION:
        _bDamp = SAFETY_DAMP_VALUE;
        _vel = omega1 / 5.0;
    }
  }
  currPWM += - limbControlScale * _bDamp * _sign * _vel * _vel;
  return currPWM;
}

// Convert current to PWM
float convertCurrentToPWM(float current) {
  float _sign = current >= 0 ? +1 : -1;
  return _sign * map(abs(current), 0, MAX_CURRENT, MINPWM, MAXPWM);
}

void sendPWMToMotor(float pwm) {
  if (pwm > 0) {
    // Move counter clockwise
    digitalWrite(MOTOR_ENABLE, HIGH);
    digitalWrite(MOTOR_DIR, LOW);
    analogWrite(MOTOR_PWM, min(MAXPWM, max(pwm, MINPWM)));
    // return min(MAXPWM, max(pwm, MINPWM));
  } else {
    // Move counter clockwise
    digitalWrite(MOTOR_ENABLE, HIGH);
    digitalWrite(MOTOR_DIR, HIGH);
    analogWrite(MOTOR_PWM, min(MAXPWM, max(-pwm, MINPWM)));
    // return -min(MAXPWM, max(-pwm, MINPWM));
  }
}

byte limitPWM(float p) {
  if (p < 0) {
    p = -p;
  }
  if (p != 0)
    p = max(0.1, min(0.9, p));
  else
    p = 0.1;
  return (byte)(p * 255);
}

// Minimum jerk trajectory function
float mjt(float t) {
  t = t > 1 ? 1.0 : t;
  t = t < 0 ? 0.0 : t;
  return 6.0 * pow(t, 5) - 15.0 * pow(t, 4) + 10 * pow(t, 3);
}

// Compute the desired position target value.
float getDesiredPositionValue() {
  if (target == INVALID_TARGET) return actual.val(0);
  float _t = runTime.num / 1000.0f;
  float _tgt = strtPos + (target - strtPos) * mjt((_t - initTime) / tgtDur);
  return min(POSITION_TARGET_MAX, max(POSITION_TARGET_MIN, _tgt));
}

// Soft limit.
float softLimit(float x, float xScale) {
  return xScale * (2 * SIGMOID(x / xScale) - 1);
}

// Error-based control scaling for safety.
float getControlScaleForScaledError(float errScaled) {
  // Left sigmoid
  float _left = SIGMOID(2 * (errScaled + 1.25));
  // Right sigmoid
  float _right = SIGMOID(2 * (errScaled - 1.25));
  return (0.96 * (_left - _right) + 0.04);
}
