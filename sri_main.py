
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
    QHBoxLayout, QTextEdit, QSizePolicy, QFrame
)

from PySide6.QtCore import (
    Qt, QTimer, QPointF, QThread, Signal, QRectF
)

from PySide6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient,
    QFont, QPainterPath, QConicalGradient
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


# ---------------- PREMIUM ANIMATED CONTROLLERS ----------------

class WaveCore(QWidget):

    def __init__(self, decorative=False, theme="cyan"):
        super().__init__()

        self.phase = 0.0
        self.rotation = 0.0
        self.mode = "IDLE"

        self.energy = 0.85
        self.target_energy = 0.85

        self.decorative = decorative
        self.theme = theme

        self.setMinimumSize(0, 0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.themes = {
            "cyan": {
                "main": QColor(0, 210, 255),
                "bright": QColor(90, 245, 255),
                "dark": QColor(0, 95, 210),
                "glow": QColor(0, 150, 255)
            },
            "multi": {
                "main": QColor(0, 225, 255),
                "bright": QColor(190, 120, 255),
                "dark": QColor(30, 100, 255),
                "glow": QColor(0, 160, 255)
            },
            "violet": {
                "main": QColor(170, 80, 255),
                "bright": QColor(255, 80, 220),
                "dark": QColor(65, 90, 255),
                "glow": QColor(140, 45, 255)
            }
        }

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(25)

    def set_mode(self, mode):

        if self.decorative:
            return

        self.mode = mode

        self.target_energy = {
            "IDLE": 0.85,
            "LISTENING": 1.35,
            "THINKING": 1.75,
            "SPEAKING": 2.1,
            "OFFLINE": 0.35
        }.get(mode, 1.0)

    def animate(self):

        self.energy += (
            self.target_energy - self.energy
        ) * 0.055

        speed = {
            "IDLE": 0.025,
            "LISTENING": 0.055,
            "THINKING": 0.075,
            "SPEAKING": 0.095,
            "OFFLINE": 0.012
        }.get(self.mode, 0.035)

        self.phase += speed
        self.rotation = (self.rotation + 0.55) % 360

        self.update()

    def draw_glow(self, painter, cx, cy, radius, color, alpha):

        gradient = QRadialGradient(
            QPointF(cx, cy),
            radius
        )

        center_color = QColor(color)
        center_color.setAlpha(alpha)

        middle_color = QColor(color)
        middle_color.setAlpha(int(alpha * 0.28))

        edge_color = QColor(color)
        edge_color.setAlpha(0)

        gradient.setColorAt(0, center_color)
        gradient.setColorAt(0.55, middle_color)
        gradient.setColorAt(1, edge_color)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)

        painter.drawEllipse(
            QPointF(cx, cy),
            radius,
            radius
        )

    def get_wave_color(self, index, alpha):

        palette = self.themes[self.theme]

        if self.theme == "multi":
            hue = int(
                (185 + index * 31 + self.phase * 17) % 360
            )

            color = QColor.fromHsv(
                hue,
                220,
                255
            )

        elif self.theme == "violet":
            colors = [
                palette["main"],
                palette["bright"],
                palette["dark"]
            ]

            color = QColor(colors[index % len(colors)])

        else:
            colors = [
                palette["main"],
                palette["bright"],
                palette["dark"]
            ]

            color = QColor(colors[index % len(colors)])

        color.setAlpha(max(0, min(255, int(alpha))))
        return color

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform
        )

        w = self.width()
        h = self.height()

        cx = w / 2
        cy = h / 2

        size = min(w, h)

        if size <= 0:
            return

        scale = size / 590.0

        palette = self.themes[self.theme]

        # PANEL BACKGROUND

        panel = QRectF(
            5,
            5,
            w - 10,
            h - 10
        )

        painter.setPen(
            QPen(
                QColor(
                    palette["main"].red(),
                    palette["main"].green(),
                    palette["main"].blue(),
                    38
                ),
                1
            )
        )

        painter.setBrush(
            QColor(4, 12, 26, 205)
        )

        painter.drawRoundedRect(
            panel,
            18,
            18
        )

        # SUBTLE BACKGROUND GRID

        painter.save()
        painter.setClipRect(panel)

        grid_gap = max(15, int(35 * scale))

        grid_color = QColor(palette["main"])
        grid_color.setAlpha(12)

        painter.setPen(QPen(grid_color, 1))

        for x in range(0, w, grid_gap):
            painter.drawLine(x, 0, x, h)

        for y in range(0, h, grid_gap):
            painter.drawLine(0, y, w, y)

        painter.restore()

        # AMBIENT LIGHT

        self.draw_glow(
            painter,
            cx,
            cy,
            245 * scale,
            palette["glow"],
            32
        )

        self.draw_glow(
            painter,
            cx,
            cy,
            145 * scale,
            palette["main"],
            25
        )

        # OUTER RINGS

        for ring in range(5):

            radius = (222 + ring * 13) * scale

            rect = QRectF(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2
            )

            direction = 1 if ring % 2 == 0 else -1

            start = int(
                (self.rotation * direction + ring * 37) * 16
            )

            color = self.get_wave_color(
                ring,
                115 - ring * 13
            )

            pen = QPen(
                color,
                max(0.7, 1.5 * scale)
            )

            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            for section in range(8):

                painter.drawArc(
                    rect,
                    start + section * 45 * 16,
                    27 * 16
                )

        # ROTATING TECHNICAL CIRCLES

        for ring in range(4):

            radius = (165 + ring * 16) * scale

            rect = QRectF(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2
            )

            direction = -1 if ring % 2 else 1

            painter.save()

            painter.translate(cx, cy)
            painter.rotate(
                self.rotation * direction * (1 + ring * 0.13)
            )
            painter.translate(-cx, -cy)

            color = self.get_wave_color(
                ring + 1,
                100 - ring * 13
            )

            painter.setPen(
                QPen(
                    color,
                    max(0.7, 1.2 * scale),
                    Qt.PenStyle.DashLine
                )
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect)

            painter.restore()

        # ROTATING TICK MARKS

        for i in range(120):

            angle = math.radians(
                i * 3 + self.rotation * (-1 if i % 2 else 1)
            )

            inner = 192 * scale
            outer = (200 if i % 5 == 0 else 196) * scale

            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner

            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer

            color = self.get_wave_color(
                i,
                155 if i % 5 == 0 else 75
            )

            painter.setPen(
                QPen(
                    color,
                    max(0.7, 1.5 * scale)
                )
            )

            painter.drawLine(
                QPointF(x1, y1),
                QPointF(x2, y2)
            )

        # ORGANIC ROTATING ENERGY WAVES

        for ring in range(7):

            base_radius = (82 + ring * 14) * scale

            path = QPainterPath()

            for i in range(361):

                angle = math.radians(
                    i + self.rotation * (1 if ring % 2 == 0 else -1)
                )

                wave1 = math.sin(
                    angle * 4 + self.phase * 2.2 + ring
                ) * 5.5

                wave2 = math.cos(
                    angle * 7 - self.phase * 1.7 + ring * 0.8
                ) * 3.5

                wave3 = math.sin(
                    angle * 12 + self.phase * 3.1
                ) * 2.0

                wave4 = math.cos(
                    angle * 2 - self.phase * 1.2
                ) * 2.0

                radius = base_radius + (
                    wave1 + wave2 + wave3 + wave4
                ) * self.energy * scale

                x = cx + math.cos(angle) * radius
                y = cy + math.sin(angle) * radius

                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            path.closeSubpath()

            color = self.get_wave_color(
                ring,
                165 - ring * 14
            )

            painter.setPen(
                QPen(
                    color,
                    max(0.8, 1.7 * scale)
                )
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # SECONDARY ENERGY WAVE

        for ring in range(3):

            radius = (105 + ring * 17) * scale

            rect = QRectF(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2
            )

            painter.save()

            painter.translate(cx, cy)
            painter.rotate(
                -self.rotation * (1.3 + ring * 0.3)
            )
            painter.translate(-cx, -cy)

            color = self.get_wave_color(
                ring + 2,
                135
            )

            painter.setPen(
                QPen(
                    color,
                    max(0.8, 1.4 * scale)
                )
            )

            painter.setBrush(Qt.BrushStyle.NoBrush)

            painter.drawArc(
                rect,
                20 * 16,
                245 * 16
            )

            painter.drawArc(
                rect,
                205 * 16,
                105 * 16
            )

            painter.restore()

        # RADIAL ENERGY BARS

        for i in range(96):

            angle = math.radians(
                i * 3.75 + self.rotation * 0.35
            )

            pulse = (
                math.sin(self.phase * 2.5 + i * 0.31) * 7
                + math.cos(self.phase * 1.8 - i * 0.55) * 5
            )

            inner = 65 * scale

            outer = inner + (
                6 + abs(pulse) * self.energy
            ) * scale

            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner

            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer

            color = self.get_wave_color(
                i,
                210 if i % 3 == 0 else 125
            )

            pen = QPen(
                color,
                max(0.7, 1.8 * scale)
            )

            pen.setCapStyle(
                Qt.PenCapStyle.RoundCap
            )

            painter.setPen(pen)

            painter.drawLine(
                QPointF(x1, y1),
                QPointF(x2, y2)
            )

        # CENTRAL CORE GLOW

        self.draw_glow(
            painter,
            cx,
            cy,
            75 * scale,
            palette["main"],
            85
        )

        # CENTRAL CORE RING

        core_radius = 48 * scale

        core_gradient = QRadialGradient(
            QPointF(cx, cy),
            core_radius
        )

        core_gradient.setColorAt(
            0,
            QColor(160, 245, 255, 150)
        )

        core_gradient.setColorAt(
            0.35,
            QColor(
                palette["main"].red(),
                palette["main"].green(),
                palette["main"].blue(),
                95
            )
        )

        core_gradient.setColorAt(
            1,
            QColor(2, 20, 60, 15)
        )

        painter.setBrush(core_gradient)

        painter.setPen(
            QPen(
                palette["bright"],
                max(1, 2 * scale)
            )
        )

        painter.drawEllipse(
            QPointF(cx, cy),
            core_radius,
            core_radius
        )

        # INNER ROTATING CORE RING

        painter.save()

        painter.translate(cx, cy)
        painter.rotate(-self.rotation * 2)
        painter.translate(-cx, -cy)

        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(
            QPen(
                palette["bright"],
                max(0.8, 1.4 * scale)
            )
        )

        painter.drawArc(
            QRectF(
                cx - 37 * scale,
                cy - 37 * scale,
                74 * scale,
                74 * scale
            ),
            20 * 16,
            255 * 16
        )

        painter.restore()

        # CORE LABEL

        painter.setPen(
            QColor(235, 252, 255)
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                max(8, int(20 * scale)),
                QFont.Weight.Bold
            )
        )

        painter.drawText(
            QRectF(
                cx - core_radius,
                cy - 14 * scale,
                core_radius * 2,
                28 * scale
            ),
            Qt.AlignmentFlag.AlignCenter,
            "SRI" if not self.decorative else "CORE"
        )

        # CONTROLLER LABEL

        if self.decorative:

            label = (
                "NEURAL LINK"
                if self.theme == "cyan"
                else "ENERGY MATRIX"
            )

        else:
            label = "SRI NEURAL CORE"

        painter.setPen(
            QColor(
                palette["bright"].red(),
                palette["bright"].green(),
                palette["bright"].blue(),
                175
            )
        )

        painter.setFont(
            QFont(
                "Consolas",
                max(7, int(9 * scale))
            )
        )

        painter.drawText(
            QRectF(
                cx - 100 * scale,
                cy + 61 * scale,
                200 * scale,
                18 * scale
            ),
            Qt.AlignmentFlag.AlignCenter,
            label
        )

        # STATUS

        if not self.decorative:

            painter.setPen(
                QColor(180, 235, 255, 190)
            )

            painter.setFont(
                QFont(
                    "Consolas",
                    max(7, int(9 * scale))
                )
            )

            painter.drawText(
                QRectF(
                    cx - 150 * scale,
                    h - 28 * scale,
                    300 * scale,
                    18 * scale
                ),
                Qt.AlignmentFlag.AlignCenter,
                "SRI NEURAL CORE // " + self.mode
            )

        # PANEL CORNER DETAILS

        painter.setPen(
            QPen(
                palette["main"],
                max(0.8, 1.2 * scale)
            )
        )

        corner = 15 * scale
        margin = 12 * scale

        for x, y, sx, sy in [
            (margin, margin, 1, 1),
            (w - margin, margin, -1, 1),
            (margin, h - margin, 1, -1),
            (w - margin, h - margin, -1, -1)
        ]:

            painter.drawLine(
                QPointF(x, y),
                QPointF(x + corner * sx, y)
            )

            painter.drawLine(
                QPointF(x, y),
                QPointF(x, y + corner * sy)
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
        self.setMinimumSize(1050, 720)

        self.setStyleSheet("""
            QWidget {
                background-color: #020711;
                color: #c8edff;
            }

            QFrame#mainPanel {
                background-color: rgba(5, 15, 31, 230);
                border: 1px solid rgba(0, 180, 255, 65);
                border-radius: 14px;
            }

            QTextEdit {
                background-color: rgba(3, 12, 25, 245);
                color: #c8edff;
                border: 1px solid rgba(0, 180, 255, 100);
                border-radius: 10px;
                padding: 12px;
                font-family: Segoe UI;
                font-size: 13px;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 12, 18, 12)
        main_layout.setSpacing(9)

        # HEADER

        header = QVBoxLayout()
        header.setSpacing(2)

        title = QLabel("S R I")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(
            QFont("Segoe UI", 28, QFont.Weight.Bold)
        )
        title.setStyleSheet(
            "color: #66eaff; background: transparent; letter-spacing: 8px;"
        )

        subtitle = QLabel(
            "PERSONAL ARTIFICIAL INTELLIGENCE SYSTEM"
        )

        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            color: #638da9;
            background: transparent;
            font-size: 10px;
            letter-spacing: 4px;
        """)

        header.addWidget(title)
        header.addWidget(subtitle)

        main_layout.addLayout(header)

        # THREE CONTROLLER PANELS

        core_layout = QHBoxLayout()
        core_layout.setSpacing(12)

        self.left_core = WaveCore(
            decorative=True,
            theme="cyan"
        )

        self.main_core = WaveCore(
            decorative=False,
            theme="multi"
        )

        self.right_core = WaveCore(
            decorative=True,
            theme="violet"
        )

        self.left_core.setMinimumSize(190, 230)
        self.main_core.setMinimumSize(300, 330)
        self.right_core.setMinimumSize(190, 230)

        core_layout.addWidget(self.left_core, 1)
        core_layout.addWidget(self.main_core, 1)
        core_layout.addWidget(self.right_core, 1)

        main_layout.addLayout(core_layout, 1)

        # SYSTEM STATUS

        self.status = QLabel("● SYSTEM STARTING")

        self.status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.status.setStyleSheet("""
            color: #00ffbd;
            background: transparent;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
            padding: 4px;
        """)

        main_layout.addWidget(self.status)

        # CONVERSATION PANEL

        self.conversation = QTextEdit()
        self.conversation.setReadOnly(True)
        self.conversation.setMinimumHeight(100)
        self.conversation.setMaximumHeight(155)

        main_layout.addWidget(self.conversation)

        # FOOTER

        self.footer = QLabel(
            "SRI SYSTEM // INITIALIZING NEURAL CORE"
        )

        self.footer.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.footer.setStyleSheet("""
            color: #668ba5;
            background: transparent;
            font-size: 10px;
            letter-spacing: 3px;
            padding: 4px;
        """)

        main_layout.addWidget(self.footer)

        self.setLayout(main_layout)

        # ASSISTANT CONNECTIONS

        self.assistant = SriAssistant()

        self.assistant.status_changed.connect(
            self.update_status
        )

        self.assistant.message_received.connect(
            self.add_message
        )

        self.assistant.start()

    def update_status(self, mode):

        # Only the central controller follows SRI status.
        # Side controllers remain decorative.

        self.main_core.set_mode(mode)

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
            "color: " + color +
            "; background: transparent;"
            "font-size: 14px;"
            "font-weight: bold;"
            "letter-spacing: 2px;"
            "padding: 4px;"
        )

        self.footer.setText(
            "SRI NEURAL SYSTEM // " + mode
        )

    def add_message(self, sender, message):

        safe_sender = html.escape(str(sender))
        safe_message = html.escape(str(message))

        sender_color = (
            "#00dfff"
            if sender == "SRI"
            else "#00ffbd"
        )

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

    # Maximized window with native Windows title bar.
    window.showMaximized()

    sys.exit(app.exec())
