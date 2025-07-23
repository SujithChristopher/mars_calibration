#!/usr/bin/env python3
"""
Load Cell & IMU Calibration Wizard
Main application entry point.
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import LoadCellCalibrationGUI


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Create and show main window
    window = LoadCellCalibrationGUI()
    window.show()
    
    # Start application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()