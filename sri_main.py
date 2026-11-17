import os
import sys
import time
import math
import ast
import operator
import re
import queue
import threading
import subprocess
import html

from collections import deque
from datetime import datetime

import numpy as np
import sounddevice as sd
import speech_recognition as sr
import speech_recognition.audio as sr_audio
import sri_controls

from google import genai
from google.genai import types

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QTextEdit, QSizePolicy
)

from PySide6.QtCore import (
    Qt, QTimer, QPointF, QThread, Signal, QRectF
)

from PySide6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient,
    QFont, QPainterPath
)


# ---------------- CONFIGURATION ----------------

FLAC_PATH = r"C:\Users\EDUKULLA DEEKSHITH\AppData\Local\Microsoft\WinGet\Packages\Xiph.FLAC_Microsoft.Winget.Source_8wekyb3d8bbwe\flac-1.5.0-win\Win64\flac.exe"

if not os.path.isfile(FLAC_PATH):
    raise FileNotFoundError("FLAC was not found. Check FLAC_PATH.")

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

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.10
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

ENERGY_THRESHOLD = 450
SILENCE_DURATION = 0.65
START_TIMEOUT = 8
MAX_RECORDING_TIME = 10

SYSTEM_INSTRUCTION = """
You are SRI, an intelligent and reliable personal AI assistant.

1. Answer directly in simple, natural language.
2. Keep normal answers concise, usually 2-5 sentences.
3. Explain complicated topics step by step when requested.
4. Correct incorrect assumptions politely.
5. Never invent facts, statistics, sources, or events.
6. Be honest when information may be outdated.
7. Understand follow-up questions using conversation history.
8. Avoid unnecessary introductions and repetitive conclusions.
9. Make answers easy to understand when spoken aloud.
10. Do not claim to have searched the internet if you have not.
"""


# ---------------- SPEECH WORKER ----------------

class SpeechWorker(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)
        self.tasks = queue.Queue()
        self.start()

    def run(self):

        speech_code = """
import sys
import pyttsx3

text = sys.argv[1]
engine = pyttsx3.init(driverName="sapi5")
engine.setProperty("rate", 175)
engine.setProperty("volume", 1.0)
engine.say(text)
engine.runAndWait()
engine.stop()
"""

        while True:
            task = self.tasks.get()

            if task is None:
                break

            text, finished = task

            try:
                result = subprocess.run(
                    [sys.executable, "-c", speech_code, text],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                if result.returncode != 0:
                    print("TTS ERROR:", result.stderr)
                else:
                    print("TTS PLAYBACK COMPLETED:", text)

            except Exception as error:
                print("TTS PROCESS ERROR:", repr(error))

            finally:
                finished.set()

    def speak(self, text):
        finished = threading.Event()
        self.tasks.put((text, finished))
        finished.wait()

    def stop(self):
        if self.is_alive():
            self.tasks.put(None)
            self.join(timeout=5)


# ---------------- ANIMATED CORE ----------------

class WaveCore(QWidget):

    def __init__(self, decorative=False):
        super().__init__()

        self.phase = 0.0
        self.rotation = 0.0
        self.mode = "IDLE"
        self.energy = 1.0
        self.target_energy = 1.0
        self.decorative = decorative

        self.setMinimumSize(0, 0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def set_mode(self, mode):
        self.mode = mode

        self.target_energy = {
            "IDLE": 0.8,
            "LISTENING": 1.5,
            "THINKING": 2.0,
            "SPEAKING": 2.4,
            "OFFLINE": 0.3
        }.get(mode, 1.0)

    def animate(self):
        self.energy += (self.target_energy - self.energy) * 0.08

        speed = {
            "IDLE": 0.025,
            "LISTENING": 0.055,
            "THINKING": 0.075,
            "SPEAKING": 0.085,
            "OFFLINE": 0.01
        }.get(self.mode, 0.035)

        self.phase += speed
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

        if scale <= 0:
            return

        # BACKGROUND GRID

        painter.setPen(QPen(QColor(0, 150, 220, 13), 1))

        grid_gap = max(18, int(45 * max(scale, 0.5)))

        for x in range(0, w, grid_gap):
            painter.drawLine(x, 0, x, h)

        for y in range(0, h, grid_gap):
            painter.drawLine(0, y, w, y)

        # AMBIENT GLOW

        glow_radius = 330 * scale

        glow = QRadialGradient(QPointF(cx, cy), glow_radius)
        glow.setColorAt(0, QColor(0, 160, 255, 48))
        glow.setColorAt(0.5, QColor(0, 90, 180, 18))
        glow.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            QPointF(cx, cy),
            glow_radius,
            glow_radius
        )

        # OUTER ROTATING HUD RINGS

        for ring in range(4):

            radius = (255 + ring * 15) * scale

            rect = QRectF(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(
                QPen(
                    QColor(0, 200, 255, max(35, 105 - ring * 18)),
                    max(0.7, 1.5 * scale)
                )
            )

            direction = 1 if ring % 2 == 0 else -1
            start = int(self.rotation * direction * 16)

            for i in range(6):
                painter.drawArc(
                    rect,
                    start + i * 60 * 16,
                    42 * 16
                )

        # INNER TECHNICAL RINGS

        for ring in range(3):

            radius = (185 + ring * 15) * scale

            rect = QRectF(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2
            )

            painter.setPen(
                QPen(
                    QColor(0, 190, 255, 75),
                    max(0.6, 1.1 * scale)
                )
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect)

        # ORGANIC REVOLVING WAVES

        for ring in range(6):

            base_radius = (105 + ring * 19) * scale
            path = QPainterPath()

            for i in range(361):

                angle = math.radians(i)

                wave1 = math.sin(
                    angle * 4 + self.phase * 2 + ring * 0.8
                ) * 6

                wave2 = math.cos(
                    angle * 7 - self.phase * 1.7 + ring
                ) * 3.5

                wave3 = math.sin(
                    angle * 13 + self.phase * 3
                ) * 1.8

                radius = base_radius + (
                    wave1 + wave2 + wave3
                ) * self.energy * scale

                x = cx + math.cos(angle) * radius
                y = cy + math.sin(angle) * radius

                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            alpha = max(25, 175 - ring * 23)

            painter.setPen(
                QPen(
                    QColor(0, 215, 255, alpha),
                    max(0.7, 1.8 * scale)
                )
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # RADIAL ENERGY BARS

        for i in range(100):

            angle = math.radians(i * 3.6)

            pulse = (
                math.sin(self.phase * 2.5 + i * 0.3) * 8
                + math.cos(self.phase * 1.8 - i * 0.6) * 6
            )

            inner = 78 * scale
            outer = inner + (5 + abs(pulse) * self.energy) * scale

            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner
            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer

            color = (
                QColor(0, 240, 255, 220)
                if i % 3 == 0
                else QColor(0, 155, 235, 140)
            )

            pen = QPen(color, max(0.7, 2 * scale))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            painter.drawLine(
                QPointF(x1, y1),
                QPointF(x2, y2)
            )

        # CENTRAL CORE

        core_radius = 65 * scale

        core = QRadialGradient(QPointF(cx, cy), core_radius)
        core.setColorAt(0, QColor(150, 245, 255, 145))
        core.setColorAt(0.55, QColor(0, 170, 240, 65))
        core.setColorAt(1, QColor(0, 40, 100, 10))

        painter.setBrush(core)
        painter.setPen(
            QPen(
                QColor(0, 225, 255, 230),
                max(0.7, 2 * scale)
            )
        )

        painter.drawEllipse(
            QPointF(cx, cy),
            core_radius,
            core_radius
        )

        # CORE LABEL

        painter.setPen(QColor(190, 250, 255))
        painter.setFont(
            QFont(
                "Segoe UI",
                max(7, int(25 * scale)),
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
            "SRI" if not self.decorative else " "
        )

        # BOTTOM STATUS ONLY — NO CLOCK OR DATE

        if not self.decorative:
            painter.setPen(QColor(0, 200, 255, 170))
            painter.setFont(QFont("Consolas", max(7, int(10 * scale))))

            painter.drawText(
                QRectF(cx - 200 * scale, h - 25 * scale,
                       400 * scale, 20 * scale),
                Qt.AlignmentFlag.AlignCenter,
                "SRI NEURAL CORE // " + self.mode
            )


# ---------------- VOICE ASSISTANT ----------------

class SriAssistant(QThread):

    status_changed = Signal(str)
    message_received = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.running = True
        self.recognizer = sr.Recognizer()
        self.recognizer.operation_timeout = 6
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.energy_threshold = ENERGY_THRESHOLD

        self.chat_sessions = {}
        self.tts = SpeechWorker()

    def stop(self):
        self.running = False

    def speak(self, text):

        if not self.running:
            return

        text = str(text).strip()

        if not text:
            return

        print("SRI SPEAKING:", text)
        self.message_received.emit("SRI", text)
        self.status_changed.emit("SPEAKING")

        self.tts.speak(text)

        if self.running:
            self.status_changed.emit("IDLE")

    def listen(self):

        self.status_changed.emit("LISTENING")

        audio_chunks = []
        previous_chunks = deque(maxlen=3)

        speech_started = False
        silence_time = 0
        start_time = time.monotonic()
        speech_start_time = None

        try:

            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                device=MIC_DEVICE,
                blocksize=CHUNK_SIZE
            ) as stream:

                while self.running:

                    data, overflowed = stream.read(CHUNK_SIZE)

                    if not self.running:
                        return ""

                    chunk = data.copy()

                    volume = np.sqrt(
                        np.mean(
                            np.square(chunk.astype(np.float32))
                        )
                    )

                    if not speech_started:

                        previous_chunks.append(chunk)

                        if volume >= ENERGY_THRESHOLD:
                            speech_started = True
                            speech_start_time = time.monotonic()
                            audio_chunks.extend(previous_chunks)

                        elif time.monotonic() - start_time >= START_TIMEOUT:
                            return ""

                    else:

                        audio_chunks.append(chunk)

                        if volume >= ENERGY_THRESHOLD:
                            silence_time = 0
                        else:
                            silence_time += CHUNK_DURATION

                        if silence_time >= SILENCE_DURATION:
                            break

                        if (
                            time.monotonic() - speech_start_time
                            >= MAX_RECORDING_TIME
                        ):
                            break

            if not audio_chunks:
                return ""

            audio_data = np.concatenate(audio_chunks, axis=0)

            audio = sr.AudioData(
                audio_data.tobytes(),
                SAMPLE_RATE,
                2
            )

            command = self.recognizer.recognize_google(
                audio,
                language="en-IN"
            )

            command = command.lower().strip()

            if command:
                self.message_received.emit("YOU", command)

            return command

        except sr.UnknownValueError:
            return ""

        except sr.RequestError as error:
            print("Recognition error:", error)
            return ""

        except Exception as error:
            print("Listening error:", error)
            return ""

    # CALCULATOR

    def calculate(self, command):

        expression = command.lower().strip()

        replacements = {
            "what is": "",
            "calculate": "",
            "how much is": "",
            "plus": "+",
            "minus": "-",
            "multiplied by": "*",
            "multiply by": "*",
            "divided by": "/",
            "divide by": "/",
            "times": "*",
            "into": "*"
        }

        for word, symbol in replacements.items():
            expression = expression.replace(word, symbol)

        number_words = {
            "zero": "0", "one": "1", "two": "2",
            "three": "3", "four": "4", "five": "5",
            "six": "6", "seven": "7", "eight": "8",
            "nine": "9", "ten": "10", "eleven": "11",
            "twelve": "12", "thirteen": "13",
            "fourteen": "14", "fifteen": "15",
            "sixteen": "16", "seventeen": "17",
            "eighteen": "18", "nineteen": "19",
            "twenty": "20"
        }

        for word, number in number_words.items():
            expression = re.sub(
                r"\b" + word + r"\b",
                number,
                expression
            )

        expression = expression.strip()

        if not re.fullmatch(r"[0-9+\-*/().\s]+", expression):
            return None

        allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos
        }

        def evaluate(node):

            if isinstance(node, ast.Expression):
                return evaluate(node.body)

            if isinstance(node, ast.Constant):
                if type(node.value) in (int, float):
                    return node.value
                raise ValueError("Invalid number")

            if isinstance(node, ast.BinOp):

                operation = allowed_operators.get(type(node.op))

                if operation is None:
                    raise ValueError("Invalid operation")

                left = evaluate(node.left)
                right = evaluate(node.right)

                if isinstance(node.op, ast.Pow) and abs(right) > 5:
                    raise ValueError("Exponent too large")

                result = operation(left, right)

                if abs(result) > 1e12:
                    raise ValueError("Result too large")

                return result

            if isinstance(node, ast.UnaryOp):

                operation = allowed_operators.get(type(node.op))

                if operation is None:
                    raise ValueError("Invalid operation")

                return operation(evaluate(node.operand))

            raise ValueError("Invalid expression")

        try:

            tree = ast.parse(expression, mode="eval")
            result = evaluate(tree)

            if isinstance(result, float) and result.is_integer():
                result = int(result)

            return f"The answer is {result}."

        except Exception:
            return None

    # LOCAL TIME

    def handle_local_time(self, command):

        patterns = [
            r"what time is it",
            r"what is the time",
            r"what's the time",
            r"tell me the time",
            r"tell me time",
            r"current time",
            r"time now",
            r"what time is it right now"
        ]

        for pattern in patterns:
            if re.fullmatch(pattern, command):
                current_time = datetime.now().strftime("%I:%M %p")
                self.speak("The current time is " + current_time)
                return True

        return False

    # LOCAL DATE

    def handle_local_date(self, command):

        patterns = [
            r"what is today's date",
            r"what's today's date",
            r"what is the date",
            r"what date is it",
            r"today's date",
            r"current date",
            r"date today"
        ]

        for pattern in patterns:
            if re.fullmatch(pattern, command):
                current_date = datetime.now().strftime("%d %B %Y")
                self.speak("Today's date is " + current_date)
                return True

        return False

    # GEMINI

    def ask_gemini(self, question):

        self.status_changed.emit("THINKING")

        for model in MODEL_LIST:

            try:

                if model not in self.chat_sessions:
                    self.chat_sessions[model] = client.chats.create(
                        model=model,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            temperature=0.4,
                            max_output_tokens=900
                        )
                    )

                response = self.chat_sessions[model].send_message(question)
                answer = response.text

                if answer and answer.strip():
                    self.speak(answer.strip())
                    return

                print(model, "returned an empty response.")

            except Exception as error:
                print(model, "failed:", repr(error))

        self.speak(
            "My AI service is unavailable right now. Please try again later."
        )

    # COMMAND PROCESSING

    def run(self):

        try:

            self.speak("Hello. I am Sri. How can I help you?")

            while self.running:

                command = self.listen()

                if not self.running:
                    break

                if not command:
                    continue

                command = command.lower().strip()

                if command in [
                    "stop", "exit", "goodbye",
                    "stop sri", "close sri"
                ]:
                    self.speak("Shutting down Sri. Goodbye.")
                    self.running = False
                    break

                if command in ["hello", "hi", "hey"]:
                    self.speak("Hello. I am listening.")
                    continue

                if "your name" in command:
                    self.speak("My name is Sri, your personal AI assistant.")
                    continue

                if "how are you" in command:
                    self.speak("I am functioning perfectly. What about you?")
                    continue

                if self.handle_local_time(command):
                    continue

                if self.handle_local_date(command):
                    continue

                answer = self.calculate(command)

                if answer is not None:
                    self.speak(answer)
                    continue

                try:

                    result = sri_controls.handle_command(command)
                    print("COMMAND RESULT:", repr(result))

                    if result:
                        self.speak(result)
                        continue

                except Exception as error:

                    print("Control error:", repr(error))
                    self.speak("I could not complete that laptop command.")
                    continue

                self.ask_gemini(command)

        except Exception as error:
            print("Assistant thread error:", repr(error))

        finally:
            self.tts.stop()
            self.running = False
            self.status_changed.emit("OFFLINE")


# ---------------- MAIN WINDOW ----------------

class SriWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("SRI - Personal AI Assistant")
        self.setMinimumSize(900, 650)

        self.setStyleSheet("""
            QWidget {
                background-color: #030912;
                color: #b8eaff;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(22, 14, 22, 14)
        main_layout.setSpacing(8)

        # HEADER

        title = QLabel("S R I")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: #00dfff;")

        subtitle = QLabel("PERSONAL AI ASSISTANT")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "color: #75bcd5; font-size: 11px; letter-spacing: 4px;"
        )

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # THREE ANIMATED CORES

        core_layout = QHBoxLayout()
        core_layout.setSpacing(8)

        self.left_core = WaveCore(decorative=True)
        self.main_core = WaveCore()
        self.right_core = WaveCore(decorative=True)

        self.left_core.setMinimumSize(150, 150)
        self.right_core.setMinimumSize(150, 150)
        self.main_core.setMinimumSize(350, 350)

        core_layout.addWidget(self.left_core, 1)
        core_layout.addWidget(self.main_core, 2)
        core_layout.addWidget(self.right_core, 1)

        main_layout.addLayout(core_layout, 1)

        # STATUS

        self.status = QLabel("● SYSTEM STARTING")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(
            "color: #00ffbd; font-size: 14px; font-weight: bold;"
        )

        main_layout.addWidget(self.status)

        # CONVERSATION PANEL

        self.conversation = QTextEdit()
        self.conversation.setReadOnly(True)
        self.conversation.setMinimumHeight(100)
        self.conversation.setMaximumHeight(155)

        self.conversation.setStyleSheet("""
            QTextEdit {
                background-color: rgba(5, 20, 36, 235);
                color: #b8eaff;
                border: 1px solid #087ca5;
                border-radius: 10px;
                padding: 12px;
                font-family: Segoe UI;
                font-size: 13px;
            }
        """)

        main_layout.addWidget(self.conversation)

        # FOOTER

        self.footer = QLabel("AWAITING COMMAND")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer.setStyleSheet(
            "color: #668ba5; font-size: 10px; letter-spacing: 2px;"
        )

        main_layout.addWidget(self.footer)

        self.setLayout(main_layout)

        # ASSISTANT CONNECTIONS

        self.assistant = SriAssistant()

        self.assistant.status_changed.connect(self.update_status)
        self.assistant.message_received.connect(self.add_message)

        self.assistant.start()

    def update_status(self, mode):

        self.main_core.set_mode(mode)
        self.left_core.set_mode(mode)
        self.right_core.set_mode(mode)

        self.status.setText("● " + mode)

        colors = {
            "LISTENING": "#00ffbd",
            "THINKING": "#ffc857",
            "SPEAKING": "#00dfff",
            "IDLE": "#668ba5",
            "OFFLINE": "#ff5555"
        }

        color = colors.get(mode, "#00dfff")

        self.status.setStyleSheet(
            "color: " + color + "; font-size: 14px; font-weight: bold;"
        )

        self.footer.setText("SRI SYSTEM // " + mode)

    def add_message(self, sender, message):

        safe_sender = html.escape(str(sender))
        safe_message = html.escape(str(message))

        sender_color = "#00dfff" if sender == "SRI" else "#00ffbd"

        self.conversation.append(
            f"<b style='color:{sender_color}'>{safe_sender}:</b> "
            f"{safe_message}"
        )

    def closeEvent(self, event):

        self.assistant.stop()
        self.assistant.wait()
        event.accept()


# ---------------- START APPLICATION ----------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = SriWindow()

    # Maximized window with Windows title bar and window controls.
    window.showMaximized()

    sys.exit(app.exec())