
import sys
import math

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient, QFont, QPainterPath
)


class WaveCore(QWidget):
    def __init__(self):
        super().__init__()

        self.phase = 0.0
        self.rotation = 0.0
        self.energy = 1.0

        self.setMinimumSize(420, 420)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def animate(self):
        self.phase += 0.025
        self.rotation = (self.rotation + 0.35) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        cx = w / 2
        cy = h / 2

        scale = min(w, h) / 750.0

        # Ambient central glow
        glow_radius = 300 * scale

        glow = QRadialGradient(
            QPointF(cx, cy), glow_radius
        )

        glow.setColorAt(0, QColor(0, 160, 255, 35))
        glow.setColorAt(0.5, QColor(0, 100, 180, 15))
        glow.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)

        painter.drawEllipse(
            QPointF(cx, cy), glow_radius, glow_radius
        )

        # Outer rotating circular outlines
        for ring in range(4):
            radius = (245 + ring * 17) * scale

            rect = QRectF(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2
            )

            color = QColor(
                0, 205, 255, 100 - ring * 15
            )

            pen = QPen(color, 1.5 * scale)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            start = int((self.rotation * (1 if ring % 2 == 0 else -1)) * 16)

            for i in range(6):
                painter.drawArc(
                    rect,
                    start + i * 5760,
                    38 * 16
                )

        # Fine technical circular outlines
        for ring in range(3):
            radius = (195 + ring * 14) * scale

            rect = QRectF(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2
            )

            pen = QPen(
                QColor(0, 180, 255, 65 + ring * 15),
                1.1 * scale
            )

            painter.setPen(pen)
            painter.drawEllipse(rect)

        # Organic revolving wave outlines
        for ring in range(6):
            base_radius = (100 + ring * 19) * scale
            path = QPainterPath()

            for i in range(361):
                angle = math.radians(i)

                wave1 = math.sin(
                    angle * 4 + self.phase * 2 + ring
                ) * 5.5

                wave2 = math.cos(
                    angle * 7 - self.phase * 1.5
                ) * 3.0

                wave3 = math.sin(
                    angle * 11 + self.phase * 2.5
                ) * 1.5

                radius = base_radius + (
                    wave1 + wave2 + wave3
                ) * scale

                x = cx + math.cos(angle) * radius
                y = cy + math.sin(angle) * radius

                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            alpha = 175 - ring * 23

            pen = QPen(
                QColor(0, 215, 255, alpha),
                1.7 * scale
            )

            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # Radial sound-wave outlines
        for i in range(100):
            angle = math.radians(i * 3.6)

            pulse = (
                math.sin(self.phase * 2 + i * 0.3) * 7
                + math.cos(self.phase * 1.5 - i * 0.4) * 5
            )

            inner = 78 * scale
            outer = inner + (8 + abs(pulse)) * scale

            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner

            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer

            color = (
                QColor(0, 235, 255, 210)
                if i % 4 == 0
                else QColor(0, 155, 230, 130)
            )

            pen = QPen(color, 1.8 * scale)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)

            painter.setPen(pen)
            painter.drawLine(
                QPointF(x1, y1),
                QPointF(x2, y2)
            )

        # Central glowing core
        core_radius = 65 * scale

        core = QRadialGradient(
            QPointF(cx, cy), core_radius
        )

        core.setColorAt(0, QColor(130, 240, 255, 120))
        core.setColorAt(0.55, QColor(0, 150, 230, 55))
        core.setColorAt(1, QColor(0, 40, 90, 10))

        painter.setBrush(core)
        painter.setPen(
            QPen(QColor(0, 220, 255, 220), 2 * scale)
        )

        painter.drawEllipse(
            QPointF(cx, cy),
            core_radius,
            core_radius
        )

        # SRI central text
        painter.setPen(QColor(150, 240, 255))

        painter.setFont(
            QFont(
                "Segoe UI",
                max(14, int(25 * scale)),
                QFont.Weight.Bold
            )
        )

        painter.drawText(
            QRectF(
                cx - core_radius,
                cy - 15 * scale,
                core_radius * 2,
                30 * scale
            ),
            Qt.AlignmentFlag.AlignCenter,
            "SRI"
        )


class SriWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SRI - Personal AI Assistant")
        self.setStyleSheet(
            "background-color: #030b16;"
        )

        self.showFullScreen()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        title = QLabel("SRI")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(
            QFont("Segoe UI", 30, QFont.Weight.Bold)
        )
        title.setStyleSheet("color: #00dfff;")

        subtitle = QLabel("PERSONAL AI ASSISTANT")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "color: #75bcd5; letter-spacing: 4px; font-size: 12px;"
        )

        self.core = WaveCore()

        status = QLabel("●  SYSTEM ONLINE")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setStyleSheet(
            "color: #00ffbd; font-size: 13px;"
        )

        footer = QLabel("AWAITING COMMAND")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            "color: #668ba5; font-size: 11px;"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(
            self.core,
            1,
            alignment=Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(status)
        layout.addWidget(footer)

        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SriWindow()
    window.show()
    sys.exit(app.exec())
