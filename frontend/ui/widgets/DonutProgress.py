from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QFont, QPainter, QPen, QBrush, QColor
from PySide6.QtCore import Qt, QRectF

class DonutProgress(QWidget):
    def __init__(self, parent=None, percentage=0):
        super().__init__(parent)
        self._percentage = percentage
        self.setFixedSize(250, 250)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw the background circle (gray)
        rect = QRectF(10, 10, self.width()-20, self.height()-20)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#F2F2F2")))
        painter.drawEllipse(rect)
        
        # Draw the progress arc (green)
        painter.setBrush(QBrush(QColor("#22C55E")))  # Tailwind green-500
        painter.drawPie(rect, 90 * 16, -self._percentage * 3.6 * 16)
        
        # Draw the inner circle to create a donut shape
        inner_rect = QRectF(35, 35, self.width()-70, self.height()-70)
        painter.setBrush(QBrush(QColor("white")))
        painter.drawEllipse(inner_rect)
        
        # Draw the percentage text in the center
        painter.setPen(QPen(QColor("#22C55E")))
        painter.setFont(QFont("Arial", 40, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{self._percentage}%")
    
    def setPercentage(self, value):
        self._percentage = max(0, min(100, value))
        self.update()