// void controller()
// {
//     fAct = -force1;
    
//     // Choosing right or left arm
//     if (des3 == 1996)
//     {
//         if (des1 > 1.5)
//         {
//             handUse = 2;//right Arm
//         }
//         else if (des1 > 0.5 && des1 <1.5)
//         {
//             handUse = 1;//left Arm
//         }
//     }
    
//     // System Calibration
//     if (des3 == 1997)
//     {
//         if (offsetCnt == 0)
//         {
//             theta1Offset = imuTheta1 - theta1Enc;
//             theta2Offset = imuTheta2 - theta2Enc;
//             theta3Offset = imuTheta3 - theta3Enc;
//             theta4Offset = imuTheta4 - theta4Enc;
//         }
        
//         offsetCnt++;
//     }
//     else 
//     {
//         offsetCnt = 0;
//     }
    
//     // angle deg to rad conversion
//     if (handUse == 2)
//     {
//         th1 = 0.0174*theta1;
//         th2 = 0.0174*theta2;
//         th3 = 0.0174*theta3;
//         th4 = 0.0174*theta4;
//         controlSense = 1.0;
//     }
//     else if (handUse == 1)
//     {
//         th1 = -0.0174*theta1;
//         th2 = -0.0174*theta2;
//         th3 = -0.0174*theta3;
//         th4 = -0.0174*theta4;
//         controlSense = -1.0;
//     }
    
//     // gravity compensation torque
//     taud = (-0.23508806876338711+0.8866366474930822*cos(th1)+1.4541005903884474*sin(th1)-8.207507701879814*cos(th2)*sin(th1)-3.2110653293552316*cos(th2)*cos(th3)*sin(th1)-0.977487496311299*sin(th1)*sin(th2)+0.6482128706723156*cos(th3)*sin(th1)*sin(th2)+0.8353582874961972*cos(th2)*sin(th1)*sin(th3)+2.255301458435932*sin(th1)*sin(th2)*sin(th3));
    
//     // Kinematic calibration values
//     if (des3 == 1999)
//     {
//         upperArm = des1;
        
//     }
    
//     if (des3 == 2000)
//     {
//         foreArm = des1;
//     }
//     if (des3 == 2001 && abs(des1) < 0.05)
//     {
//         shx = des1;
//     }
//     if (des3 == 2002 && abs(des1) < 0.05)
//     {
//         shy = des1;
//     }
//     if (des3 == 2003 && des1 < 0.5 && des1 > 0.2)
//     {
//         shz = des1;
//     }
    
//     //arm weight support values
//     if (des3 == 2004)
//     {
//         W1 = des1;
//     }
//     if (des3 == 2005)
//     {
//         W2 = des1;
//     }
    
//     // torque control
//     if (des3 == 2006 && PCParam == 0x00)
//     {

//         stat++;
        
//         if (des1 > 0.1)
//         {
//             support = des1;
//         }
//         else
//         {
//             support = 0.0;
//         }
        
//         // arm inverse kinematics
//         endx = cos(th1)*(0.475*cos(th2)+0.291*cos(th2+th3));
//         endy = sin(th1)*(0.475*cos(th2)+0.291*cos(th2+th3));
//         endz = -0.475*sin(th2)-0.291*sin(th2+th3);
        
//         zvec1 = cos(th1)*cos(th2+th3+th4);
//         zvec2 = sin(th1)*cos(th2+th3+th4);
//         zvec3 = -sin(th2+th3+th4);
        
//         elbx = endx - foreArm*zvec1;
//         elby = endy - foreArm*zvec2;
//         elbz = endz - foreArm*zvec3;
        
//         fAx = foreArm*zvec1;
//         fAy = foreArm*zvec2;
//         fAz = foreArm*zvec3;
        
//         uAx = elbx - shx;
//         uAy = elby - shy;
//         uAz = elbz - shz;
        
//         phi1 = abs(atan2(endy,endx));
//         if (abs(uAz) <= upperArm)
//         {
//             phi2 = asin(uAz/upperArm);
//         }
//         else
//         {
//             phi2 = -1.57;
//         }
        
//         dot = (uAx*fAx + uAy*fAy + uAz*fAz)/(upperArm*foreArm);
        
//         if ( dot > 1 || dot < -1)
//         {
//             phi4 = 0;
//         }
//         else
//         {
//             phi4 = acos((uAx*fAx + uAy*fAy + uAz*fAz)/(foreArm*upperArm));
//         }
        
//         if (support > 1)
//         {
//             support = 1;  
//         }
//         else if (support < 0)
//         {
//             support = 0;
//         }
        
//         if (isnan(phi1)||isnan(phi2)||isnan(phi4))
//         {
            
//         }
//         else
//         {
//             if (endy < 0)
//             {
//                 distFromZAxis = pow(endx*endx + endy*endy, 0.5);
//             }
//             else
//             {
//                 distFromZAxis = -pow(endx*endx + endy*endy, 0.5);
//             }
            
//             sigmoid = 1/(1+exp(-(distFromZAxis-meanx)/spreadx));
//             sigmoidFlex = 1 - 1/(1 + exp(-(abs(theta1)- meanFlex)/spreadFlex));
            
//             // shoulder torque calculation
//             tarm = sigmoidFlex*sigmoid*sigmoid*((W1*cos(phi2) + W2*cos(phi2 - phi4))*sin(phi1));
            
//             fDes = (support*(tarm/pow(endx*endx + endy*endy,0.5)));
            
//             if ((fDes - fDesiminus1) > 0.05 && PCParam < 1 && PCParam == PCParamiminus1)
//             {
//                 fDes = fDesiminus1 + 0.05 * (fDes - fDesiminus1)/abs(fDes-fDesiminus1);
//             }
            
//         }
//     }
//     else
//     {
//         fDes = 0;
//         tarm = 0;
//         tweight = 0;
//     }
    
//     // torque controller
//     if (PCParam == 0x00 && des3 > 1000)
//     {
//         Kp_theta1 = 3.0;
//         Kd_theta1 = 2.0;
        
//         endy = sin(th1)*(0.475*cos(th2)+0.291*cos(th2+th3));
//         tact = fAct*pow(endx*endx + endy*endy,0.5);
//         errorForce = (support*tarm - tact);
        
//         controllaw_theta1 = Kp_theta1*errorForce - Kd_theta1*errorForcei + taud + support*tarm;
//         controllaw_theta1 = controlSense*controllaw_theta1;
//         motorcurrent_theta1 = controllaw_theta1/3.35;
//     }
    
//     // position comtroller
//     else if (PCParam == 1001)
//     {
//         if (controlSense == 1)
//         {
//             theta1d = des2;
//             Kp_theta1 = 5.0;
//             Kd_theta1 = 17.5;
//             error_theta1 = (theta1 - theta1d);
//             errord_theta1 = theta1 - theta1iminus1; 
//             controllaw_theta1 = (Kp_theta1*error_theta1 - Kd_theta1*errord_theta1 + taud);
//         }
//         else if (controlSense == -1)
//         {
//             theta1d = des2;
//             Kp_theta1 = 5.0;
//             Kd_theta1 = -17.5;
//             error_theta1 = (theta1 - theta1d);
//             errord_theta1 = theta1 - theta1iminus1; 
//             controllaw_theta1 = (Kp_theta1*error_theta1 - Kd_theta1*errord_theta1 - taud);
//         }
        
//         controllaw_theta1 = controllaw_theta1;
//         motorcurrent_theta1 = controllaw_theta1/3.35;
//     }
    
//     PWM_theta1 = 409.6 + 353.1*abs(motorcurrent_theta1);
    
//     analogWrite(MOTOR_PWM, min(PWM_theta1,3600));
//     digitalWrite(MOTOR_ENABLE, HIGH);
    
//     if (controllaw_theta1 > 0)
//     {
//         digitalWrite(MOTOR_DIR,LOW);
//     }
//     else
//     {
//         digitalWrite(MOTOR_DIR, HIGH);
//     }
    
//     erroriminus1_theta1 = error_theta1;
//     theta1iminus1 = theta1;
//     errorForcei = errorForce;
//     fActiminus1 = fAct;
//     fDesiminus1 = fDes;
//     PCParamiminus1 = PCParam;
    
    
// }
