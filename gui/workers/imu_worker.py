"""
IMU data worker thread for parsing and handling IMU sensor data.
"""

import serial
from PySide6.QtCore import QObject, Signal


class IMUDataWorker(QObject):
    """Worker thread for parsing IMU data"""
    data_received = Signal(dict)
    connection_lost = Signal()
    
    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
        
    def start_connection(self):
        """Start IMU serial connection and reading loop"""
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            self.read_loop()
        except Exception as e:
            self.data_received.emit({"error": f"Connection error: {str(e)}"})
            
    def read_loop(self):
        """Continuously read and parse IMU data"""
        while self.running and self.serial_connection:
            try:
                if self.serial_connection.in_waiting:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    if line:
                        # Check for calculated offset values first
                        parsed_offset = self.parse_offset_line(line)
                        if parsed_offset:
                            self.data_received.emit(parsed_offset)
                        else:
                            # Try parsing CSV data
                            parsed_data = self.parse_imu_data(line)
                            if parsed_data:
                                self.data_received.emit(parsed_data)
                            else:
                                # Send raw message for display
                                self.data_received.emit({"raw_message": line})
            except Exception as e:
                self.connection_lost.emit()
                break
                
    def parse_imu_data(self, data_line):
        """Parse IMU data line: AX,AY,AZ,ROLL,PITCH,YAW,OFFSET_X,OFFSET_Y,OFFSET_Z"""
        try:
            if ',' in data_line and not data_line.startswith('='):
                parts = data_line.split(',')
                if len(parts) >= 9:
                    return {
                        'ax': float(parts[0]),
                        'ay': float(parts[1]),
                        'az': float(parts[2]),
                        'roll': float(parts[3]),
                        'pitch': float(parts[4]),
                        'yaw': float(parts[5]),
                        'offset_x': float(parts[6]),
                        'offset_y': float(parts[7]),
                        'offset_z': float(parts[8])
                    }
        except (ValueError, IndexError):
            pass
        return None

    def parse_offset_line(self, line):
        """Parse calculated offset lines from Arduino calibration output"""
        try:
            # Parse "IMU1 Pitch Offset: -0.025858" format
            if "IMU1 Pitch Offset:" in line or "IMU1PITCHOFFSET:" in line:
                value = float(line.split(":")[-1].strip())
                return {"calibrated_pitch_offset": value}

            # Parse "IMU1 Roll Offset: -0.087844" format
            elif "IMU1 Roll Offset:" in line or "IMU1ROLLOFFSET:" in line:
                value = float(line.split(":")[-1].strip())
                return {"calibrated_roll_offset": value}

            # Parse "IMU2 Roll Offset: 0.000000" format
            elif "IMU2 Roll Offset:" in line or "IMU2ROLLOFFSET:" in line:
                value = float(line.split(":")[-1].strip())
                return {"calibrated_imu2_roll_offset": value}

            # Parse "IMU3 Roll Offset: 0.000000" format
            elif "IMU3 Roll Offset:" in line or "IMU3ROLLOFFSET:" in line:
                value = float(line.split(":")[-1].strip())
                return {"calibrated_imu3_roll_offset": value}

        except (ValueError, IndexError):
            pass
        return None
            
    def send_data(self, data):
        """Send data to serial port"""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(data.encode('utf-8'))
                return True
            except Exception as e:
                self.data_received.emit({"error": f"Send error: {str(e)}"})
                return False
        return False
        
    def stop_connection(self):
        """Stop IMU serial connection"""
        self.running = False
        if self.serial_connection:
            self.serial_connection.close()