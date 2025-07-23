"""
Serial worker thread for handling load cell communication.
"""

import serial
from PySide6.QtCore import QObject, Signal


class SerialWorker(QObject):
    """Worker thread for handling serial communication"""
    data_received = Signal(str)
    connection_lost = Signal()
    
    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
        
    def start_connection(self):
        """Start serial connection and reading loop"""
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            self.read_loop()
        except Exception as e:
            self.data_received.emit(f"Connection error: {str(e)}")
            
    def read_loop(self):
        """Continuously read from serial port"""
        while self.running and self.serial_connection:
            try:
                if self.serial_connection.in_waiting:
                    data = self.serial_connection.readline().decode('utf-8').strip()
                    if data:
                        self.data_received.emit(data)
            except Exception as e:
                self.connection_lost.emit()
                break
                
    def send_data(self, data):
        """Send data to serial port"""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(data.encode('utf-8'))
                return True
            except Exception as e:
                self.data_received.emit(f"Send error: {str(e)}")
                return False
        return False
        
    def stop_connection(self):
        """Stop serial connection"""
        self.running = False
        if self.serial_connection:
            self.serial_connection.close()