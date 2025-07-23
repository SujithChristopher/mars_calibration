"""
Angle indicator widget for displaying IMU angle values with visual arc.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont


class AngleIndicator(QWidget):
    """Custom widget for displaying angle values with visual arc"""
    
    def __init__(self, title, min_angle=-180, max_angle=180, color=QColor(33, 150, 243)):
        super().__init__()
        self.title = title
        self.angle = 0.0
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.color = color
        self.setMinimumSize(150, 150)
        
    def set_angle(self, angle):
        self.angle = max(self.min_angle, min(self.max_angle, angle))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 20
        
        # Draw background circle
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawEllipse(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        
        # Draw angle arc
        painter.setPen(QPen(self.color, 4))
        start_angle = 90 * 16  # Start from top (90 degrees in 1/16th degree units)
        span_angle = -int((self.angle / 180.0) * 180 * 16)  # Convert to 1/16th degrees
        painter.drawArc(center.x() - radius, center.y() - radius, radius * 2, radius * 2, start_angle, span_angle)
        
        # Draw center dot
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(center.x() - 3, center.y() - 3, 6, 6)
        
        # Draw angle text
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        angle_text = f"{self.angle:.1f}°"
        painter.drawText(rect, Qt.AlignCenter | Qt.AlignBottom, angle_text)
        
        # Draw title
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter | Qt.AlignTop, self.title)