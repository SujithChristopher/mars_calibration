/* Functions to handle robot and human limb related computations for control, 
 * data communication for the MARS robot.
 *  
 *  Author: Sivakumar Balasubramanian.
 *  Date: 01 July 2025
 */

void updateEndpointPosition()
{
  float _temp = L1 * cos2 + L2 * cos(theta2r + theta3r);
  xEp = cos1 * _temp;
  yEp = sin1 * _temp;
  zEp = - L1 * sin2 - L2 * sin(theta2r + theta3r);
}

float getMarsGravityCompensationTorque()
{
  return (marsGCParam[0] * cos1
          + marsGCParam[1] * sin1
          + marsGCParam[2] * cos2 * sin1
          + marsGCParam[3] * cos2 * cos3 * sin1
          + marsGCParam[4] * sin1 * sin2
          + marsGCParam[5] * cos3 * sin1 * sin2
          + marsGCParam[6] * cos2 * sin1 * sin3
          + marsGCParam[7] * sin1 * sin2 * sin3);
}
