
import os
import sys
import time
import math

import sounddevice as sd
import speech_recognition as sr
import speech_recognition.audio as sr_audio
import pyttsx3

import sri_controls

from datetime import datetime
from google import genai

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QTextEdit
)

from PySide6.QtCore import (
    Qt, QTimer, QPointF, QThread, Signal
)

from PySide6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient, QFont
)


# ---------------- CONFIGURATION ----------------

FLAC_PATH = r"C:\Users\EDUKULLA DEEKSHITH\AppData\Local\Microsoft\WinGet\Packages\Xiph.FLAC_Microsoft.Winget.Source_8wekyb3d8bbwe\flac-1.5.0-win\Win64\flac.exe"

if not os.path.isfile(FLAC_PATH):
    raise FileNotFoundError(
        "FLAC was not found. Check the FLAC_PATH in sri_main.py."
    )

sr_audio.get_flac_converter = lambda: FLAC_PATH

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "Gemini API key not found. Set GEMINI_API_KEY in PowerShell."
    )

client = genai.Client(api_key=API_KEY)

MODEL_LIST = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite"
]

MIC_DEVICE = 1


# ---------------- ANIMATED CORE ----------------

class WaveCore(QWidget):

    def __init__(self):
        super().__init__()

        self.phase = 0
        self.mode = "IDLE"

        self.setFixedSize(420, 420)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def animate(self):

        speed = {
            "LISTENING": 0.10,
            "THINKING": 0.16,
            "SPEAKING": 0.13,
            "IDLE": 0.035
        }

        self.phase += speed.get(self.mode, 0.05)
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        cx = self.width() / 2
        cy = self.height() / 2

        glow = QRadialGradient(QPointF(cx, cy), 190)
        glow.setColorAt(0, QColor(0, 150, 220, 40))
        glow.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 190, 190)

        for ring in range(5):

            radius_base = 95 + ring * 17
            points = []

            for i in range(361):

                angle = math.radians(i)

                wave = math.sin(
                    angle * 5 + self.phase * 2 + ring
                ) * 5

                wave += math.sin(
                    angle * 9 - self.phase
                ) * 2

                radius = radius_base + wave

                x = cx + math.cos(angle) * radius
                y = cy + math.sin(angle) * radius

                points.append(QPointF(x, y))

            alpha = 155 - ring * 22

            painter.setPen(
                QPen(QColor(0, 205, 255, alpha), 1.8)
            )

            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        for i in range(72):

            angle = math.radians(i * 5)

            strength = (
                math.sin(self.phase * 2 + i * 0.35) * 7
                + math.sin(self.phase + i * 0.7) * 5
            )

            if self.mode == "THINKING":
                strength *= 1.5

            if self.mode == "IDLE":
                strength *= 0.4

            inner = 83
            outer = inner + 9 + abs(strength)

            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner

            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer

            painter.setPen(
                QPen(QColor(0, 225, 255, 190), 2)
            )

            painter.drawLine(
                QPointF(x1, y1),
                QPointF(x2, y2)
            )

        core = QRadialGradient(QPointF(cx, cy), 75)

        core.setColorAt(0, QColor(0, 220, 255, 110))
        core.setColorAt(0.55, QColor(0, 100, 180, 70))
        core.setColorAt(1, QColor(0, 30, 70, 10))

        painter.setBrush(core)
        painter.setPen(QPen(QColor(0, 220, 255), 2))
        painter.drawEllipse(QPointF(cx, cy), 67, 67)

        painter.setBrush(QColor(3, 20, 38))
        painter.setPen(QPen(QColor(0, 220, 255), 2))
        painter.drawEllipse(QPointF(cx, cy), 49, 49)

        painter.setPen(QColor(100, 235, 255))
        painter.setFont(
            QFont("Segoe UI", 25, QFont.Weight.Bold)
        )

        painter.drawText(
            int(cx - 35), int(cy + 9), "SRI"
        )


# ---------------- VOICE ASSISTANT THREAD ----------------

class SriAssistant(QThread):

    status_changed = Signal(str)
    message_received = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.running = True
        self.recognizer = sr.Recognizer()
        self.chat_sessions = {}

    def stop(self):
        self.running = False

    def speak(self, text):

        if not self.running:
            return

        self.message_received.emit("SRI", text)
        self.status_changed.emit("SPEAKING")

        engine = pyttsx3.init()
        engine.setProperty("rate", 160)
        engine.setProperty("volume", 1.0)

        engine.say(text)
        engine.runAndWait()
        engine.stop()

        time.sleep(0.3)

    def listen(self):

        self.status_changed.emit("LISTENING")

        try:

            recording = sd.rec(
                int(5 * 16000),
                samplerate=16000,
                channels=1,
                dtype="int16",
                device=MIC_DEVICE
            )

            sd.wait()

            if not self.running:
                return ""

            audio = sr.AudioData(
                recording.tobytes(), 16000, 2
            )

            command = self.recognizer.recognize_google(audio)

            self.message_received.emit("YOU", command)

            return command.lower().strip()

        except sr.UnknownValueError:
            return ""

        except sr.RequestError as error:

            print("Recognition error:", error)

            self.speak(
                "I am unable to connect to the recognition service."
            )

            return ""

        except Exception as error:

            print("Listening error:", error)
            return ""

    def ask_gemini(self, question):

        self.status_changed.emit("THINKING")

        for model in MODEL_LIST:

            try:

                if model not in self.chat_sessions:

                    self.chat_sessions[model] = client.chats.create(
                        model=model
                    )

                response = self.chat_sessions[model].send_message(
                    question
                )

                answer = response.text

                if answer:

                    self.speak(answer)
                    return

            except Exception as error:

                print(model, "failed:", error)

        self.speak(
            "My AI service is unavailable right now. Please try again later."
        )

    def run(self):

        self.speak(
            "Hello. I am Sri. Your personal AI assistant is ready."
        )

        while self.running:

            command = self.listen()

            if not self.running:
                break

            if not command:
                continue

            command = command.lower().strip()

            # EXIT COMMANDS

            if command in [
                "stop",
                "exit",
                "goodbye",
                "stop sri",
                "close sri"
            ]:

                self.speak("Shutting down Sri. Goodbye.")
                self.running = False
                break

            # LAPTOP CONTROL COMMANDS

            try:

                result = sri_controls.handle_command(command)

                if result:

                    self.speak(result)
                    continue

            except Exception as error:

                print("Control error:", error)

                self.speak(
                    "I could not complete that laptop command."
                )

                continue

            # BASIC CONVERSATION

            if command in ["hello", "hi", "hey"]:

                self.speak("Hello. I am listening.")

            elif "your name" in command:

                self.speak(
                    "My name is Sri, your personal AI assistant."
                )

            elif "how are you" in command:

                self.speak(
                    "I am functioning perfectly. What about you?"
                )

            elif "time" in command:

                current_time = datetime.now().strftime("%I:%M %p")

                self.speak(
                    "The current time is " + current_time
                )

            elif "date" in command:

                current_date = datetime.now().strftime("%d %B %Y")

                self.speak(
                    "Today's date is " + current_date
                )

            # GENERAL AI QUESTIONS

            else:

                self.ask_gemini(command)

        self.status_changed.emit("OFFLINE")


# ---------------- MAIN GUI ----------------

class SriWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("SRI - Personal AI Assistant")
        self.setFixedSize(700, 790)

        self.setStyleSheet(
            "background-color: #030b16;"
        )

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        title = QLabel("SRI")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title.setFont(
            QFont("Segoe UI", 30, QFont.Weight.Bold)
        )

        title.setStyleSheet("color: #00dfff;")

        subtitle = QLabel("PERSONAL AI ASSISTANT")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle.setStyleSheet(
            "color: #75bcd5; font-size: 12px;"
        )

        self.core = WaveCore()

        self.status = QLabel("● SYSTEM STARTING")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status.setStyleSheet(
            "color: #00ffbd; font-size: 13px;"
        )

        self.conversation = QTextEdit()
        self.conversation.setReadOnly(True)
        self.conversation.setFixedHeight(145)

        self.conversation.setStyleSheet("""
            QTextEdit {
                background-color: #071525;
                color: #b8eaff;
                border: 1px solid #123c55;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }
        """)

        self.footer = QLabel("SRI INITIALIZING...")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.footer.setStyleSheet(
            "color: #668ba5; font-size: 11px;"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(
            self.core,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(self.status)
        layout.addWidget(self.conversation)
        layout.addWidget(self.footer)

        self.setLayout(layout)

        self.assistant = SriAssistant()

        self.assistant.status_changed.connect(
            self.update_status
        )

        self.assistant.message_received.connect(
            self.add_message
        )

        self.assistant.start()

    def update_status(self, mode):

        self.core.set_mode(mode)

        self.status.setText("● " + mode)

        colors = {
            "LISTENING": "#00ffbd",
            "THINKING": "#ffc857",
            "SPEAKING": "#00dfff",
            "IDLE": "#668ba5",
            "OFFLINE": "#ff5555"
        }

        self.status.setStyleSheet(
            "color: " + colors.get(mode, "#00dfff")
            + "; font-size: 13px;"
        )

        self.footer.setText(
            "SRI IS " + mode
        )

    def add_message(self, sender, message):

        self.conversation.append(
            f"<b style='color:#00dfff'>{sender}:</b> "
            f"{message}"
        )

    def closeEvent(self, event):

        self.assistant.stop()
        self.assistant.wait()

        event.accept()


# ---------------- START APPLICATION ----------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = SriWindow()
    window.show()

    sys.exit(app.exec())
