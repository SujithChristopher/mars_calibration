"""
Step indicator widget for showing progress in load cell calibration workflow.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class StepIndicator(QWidget):
    """Custom widget for showing step progress with checkmarks"""
    
    def __init__(self, step_number, title, description):
        super().__init__()
        self.step_number = step_number
        self.title = title
        self.description = description
        self.is_completed = False
        self.is_current = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Step circle/checkmark
        self.step_label = QLabel()
        self.step_label.setFixedSize(40, 40)
        self.step_label.setAlignment(Qt.AlignCenter)
        self.step_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                border-radius: 20px;
                background-color: #f0f0f0;
                color: #666;
                font-weight: bold;
                font-size: 16px;
            }
        """)
        self.step_label.setText(str(self.step_number))
        
        # Text content
        text_layout = QVBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.desc_label = QLabel(self.description)
        self.desc_label.setFont(QFont("Arial", 10))
        self.desc_label.setStyleSheet("color: #666;")
        
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        text_layout.addStretch()
        
        layout.addWidget(self.step_label)
        layout.addLayout(text_layout)
        layout.addStretch()
        
        self.update_appearance()
        
    def set_completed(self, completed=True):
        self.is_completed = completed
        self.update_appearance()
        
    def set_current(self, current=True):
        self.is_current = current
        self.update_appearance()
        
    def update_appearance(self):
        if self.is_completed:
            self.step_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 20px;
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.step_label.setText("✓")
            self.title_label.setStyleSheet("color: #4CAF50;")
        elif self.is_current:
            self.step_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #2196F3;
                    border-radius: 20px;
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.step_label.setText(str(self.step_number))
            self.title_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        else:
            self.step_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #ccc;
                    border-radius: 20px;
                    background-color: #f0f0f0;
                    color: #666;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.step_label.setText(str(self.step_number))
            self.title_label.setStyleSheet("color: #333;")