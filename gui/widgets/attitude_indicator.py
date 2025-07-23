"""
3D attitude indicator widget showing pitch and roll with artificial horizon.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QLinearGradient


class AttitudeIndicator(QWidget):
    """3D attitude indicator widget showing pitch and roll"""
    
    def __init__(self):
        super().__init__()
        self.pitch = 0.0
        self.roll = 0.0
        self.setMinimumSize(200, 200)
        
    def set_attitude(self, pitch, roll):
        self.pitch = pitch
        self.roll = roll
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 10
        
        # Create gradient for sky/ground
        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, QColor(135, 206, 235))  # Sky blue
        gradient.setColorAt(0.5, QColor(255, 255, 255))  # Horizon
        gradient.setColorAt(1, QColor(139, 69, 19))  # Brown earth
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        
        # Rotate and translate for attitude
        painter.translate(center)
        painter.rotate(self.roll)
        painter.translate(0, self.pitch * 2)  # Scale pitch movement
        
        # Draw attitude background
        painter.drawEllipse(-radius, -radius, radius * 2, radius * 2)
        
        painter.resetTransform()
        painter.translate(center)
        
        # Draw aircraft symbol (fixed)
        painter.setPen(QPen(QColor(255, 255, 0), 3))  # Yellow
        painter.drawLine(-30, 0, -10, 0)  # Left wing
        painter.drawLine(10, 0, 30, 0)    # Right wing
        painter.drawLine(0, -5, 0, 5)     # Center line
        
        # Draw outer ring
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(-radius, -radius, radius * 2, radius * 2)
        
        # Draw pitch/roll text
        painter.setPen(QPen(QColor(50, 50, 50), 1))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(-radius, radius + 15, f"P: {self.pitch:.1f}°")
        painter.drawText(radius - 50, radius + 15, f"R: {self.roll:.1f}°")