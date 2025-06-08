from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import (QFont, QPainter, QColor, QPen, QFontDatabase, 
                          QLinearGradient, QRadialGradient, QPainterPath)
import math

class GaugeWidget(QWidget):
    def __init__(self, value, threshold):
        super().__init__()
        self._value = 0  # Start from 0 for animation
        self.target_value = value
        self.threshold = threshold
        self.setup_ui()
        self.setup_animation()
        
    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 200)
        
    def setup_animation(self):
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(1000)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.target_value)
        self.animation.start()

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
        self.update()

    value = Property(float, get_value, set_value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate dimensions based on widget size
        side = min(self.width(), self.height())
        margin = side * 0.1
        rect = QRectF(margin, margin, side - 2*margin, side - 2*margin)
        
        self.draw_background(painter, rect)
        self.draw_gauge(painter, rect)
        self.draw_value(painter, rect)
        self.draw_decorations(painter, rect)

    def draw_background(self, painter, rect):
        # Draw shadow
        painter.setPen(Qt.NoPen)
        shadow_gradient = QRadialGradient(rect.center(), rect.width()/2)
        shadow_gradient.setColorAt(0.95, QColor(0, 0, 0, 30))
        shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(shadow_gradient)
        painter.drawEllipse(rect.adjusted(-5, -5, 5, 5))

        # Draw full circle background
        painter.setPen(QPen(QColor("#e0e0e0"), rect.width() * 0.1, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)  # Full circle background

    def draw_gauge(self, painter, rect):
        # Draw value arc with gradient
        color = self.get_arc_color(self.value)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(1, color)
        
        pen = QPen()
        pen.setBrush(gradient)
        pen.setWidth(int(rect.width() * 0.1))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # Draw full circle progress
        span_angle = (self.value * 360 / 100) * 16  # Full circle progress
        painter.drawArc(rect, 90 * 16, -span_angle)  # Start from top (90 degrees)

    def draw_value(self, painter, rect):
        # Draw center circle
        center_radius = rect.width() * 0.3
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        center_rect = QRectF(
            rect.center().x() - center_radius,
            rect.center().y() - center_radius,
            center_radius * 2,
            center_radius * 2
        )
        painter.drawEllipse(center_rect)
        
        # Draw value text
        font_size = int(rect.width() * 0.2)
        font = QFont("Arial", font_size, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#333333"))
        
        # Draw percentage
        text = f"{int(self.value)}%"
        text_rect = QRectF(center_rect)
        painter.drawText(text_rect, Qt.AlignCenter, text)

    def draw_decorations(self, painter, rect):
        # Draw tick marks around the full circle
        painter.setPen(QPen(QColor("#cccccc"), 2))
        center = rect.center()
        outer_radius = rect.width() * 0.48
        inner_radius = rect.width() * 0.45
        
        for i in range(0, 360, 30):  # Draw marks every 30 degrees around full circle
            angle = math.radians(i)
            cos_angle = math.cos(angle)
            sin_angle = math.sin(angle)
            
            start_x = center.x() + outer_radius * cos_angle
            start_y = center.y() - outer_radius * sin_angle
            end_x = center.x() + inner_radius * cos_angle
            end_y = center.y() - inner_radius * sin_angle
            
            painter.drawLine(start_x, start_y, end_x, end_y)

    def get_arc_color(self, value):
        if value >= self.threshold["good"]:
            return QColor("#10B981")
        elif value >= self.threshold["moderate"]:
            return QColor("#F59E0B")
        else:
            return QColor("#EF4444")

class MetricWidget(QFrame):
    def __init__(self, title, value, threshold):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignCenter)  # Center the layout contents
        
        # Title without border
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.DemiBold))
        title_label.setStyleSheet("color: #374151; border : none")
        title_label.setAlignment(Qt.AlignCenter)  # Center the title text
        layout.addWidget(title_label)
        
        # Gauge widget
        gauge = GaugeWidget(value, threshold)
        layout.addWidget(gauge, alignment=Qt.AlignCenter)  # Center the gauge
        
        layout.addStretch()

class FeedbackGaugeWidget(QWidget):
    def __init__(self, value, max_value):
        super().__init__()
        self._value = 0
        self.target_value = value
        self.max_value = max_value
        self.setup_ui()
        self.setup_animation()

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 200)

    def setup_animation(self):
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(1000)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.target_value)
        self.animation.start()

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
        self.update()

    value = Property(float, get_value, set_value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        margin = side * 0.1
        rect = QRectF(margin, margin, side - 2*margin, side - 2*margin)

        self.draw_background(painter, rect)
        self.draw_gauge(painter, rect)
        self.draw_value(painter, rect)
        self.draw_decorations(painter, rect)

    def draw_background(self, painter, rect):
        painter.setPen(Qt.NoPen)
        shadow_gradient = QRadialGradient(rect.center(), rect.width()/2)
        shadow_gradient.setColorAt(0.95, QColor(0, 0, 0, 30))
        shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(shadow_gradient)
        painter.drawEllipse(rect.adjusted(-5, -5, 5, 5))

        painter.setPen(QPen(QColor("#e0e0e0"), rect.width() * 0.1, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)  # Full circle background

    def draw_gauge(self, painter, rect):
        percentage = min(100, (self.value / self.max_value) * 100)
        color = self.get_feedback_color(percentage)
        
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(1, color)
        
        pen = QPen()
        pen.setBrush(gradient)
        pen.setWidth(int(rect.width() * 0.1))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        span_angle = (percentage * 360 / 100) * 16  # Full circle progress
        painter.drawArc(rect, 90 * 16, -span_angle)  # Start from top

    def draw_value(self, painter, rect):
        center_radius = rect.width() * 0.3
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        center_rect = QRectF(
            rect.center().x() - center_radius,
            rect.center().y() - center_radius,
            center_radius * 2,
            center_radius * 2
        )
        painter.drawEllipse(center_rect)
        
        font_size = int(rect.width() * 0.2)
        font = QFont("Arial", font_size, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#333333"))
        
        text = str(int(self.value))
        text_rect = QRectF(center_rect)
        painter.drawText(text_rect, Qt.AlignCenter, text)

    def draw_decorations(self, painter, rect):
        painter.setPen(QPen(QColor("#cccccc"), 2))
        center = rect.center()
        outer_radius = rect.width() * 0.48
        inner_radius = rect.width() * 0.45
        
        for i in range(0, 360, 30):  # Full circle tick marks
            angle = math.radians(i)
            cos_angle = math.cos(angle)
            sin_angle = math.sin(angle)
            
            start_x = center.x() + outer_radius * cos_angle
            start_y = center.y() - outer_radius * sin_angle
            end_x = center.x() + inner_radius * cos_angle
            end_y = center.y() - inner_radius * sin_angle
            
            painter.drawLine(start_x, start_y, end_x, end_y)

    def get_feedback_color(self, percentage):
        if percentage < 33:
            return QColor("#10B981")
        elif percentage < 66:
            return QColor("#F59E0B")
        else:
            return QColor("#EF4444")

class FeedbackMetricWidget(QFrame):
    def __init__(self, title, value, max_value):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignCenter)
        
        # Title without border
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.DemiBold))
        title_label.setStyleSheet("color: #374151; border: none")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Gauge widget
        self.gauge = FeedbackGaugeWidget(value, max_value)
        layout.addWidget(self.gauge, alignment=Qt.AlignCenter)
        
        layout.addStretch()
        
    def update_value(self, value):
        """Update the gauge value and trigger animation"""
        # Update the gauge's target value
        self.gauge.target_value = value
        
        # Reset and restart the animation
        self.gauge.animation.setStartValue(self.gauge.value)
        self.gauge.animation.setEndValue(value)
        self.gauge.animation.start()