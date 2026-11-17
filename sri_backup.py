
import os
import time
import sounddevice as sd
import speech_recognition as sr
import speech_recognition.audio as sr_audio
import pyttsx3
from google import genai
from datetime import datetime

# FLAC path for Windows ARM64
FLAC_PATH = r"C:\Users\EDUKULLA DEEKSHITH\AppData\Local\Microsoft\WinGet\Packages\Xiph.FLAC_Microsoft.Winget.Source_8wekyb3d8bbwe\flac-1.5.0-win\Win64\flac.exe"

sr_audio.get_flac_converter = lambda: FLAC_PATH

# Gemini configuration
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("Gemini API key not found. Set GEMINI_API_KEY in PowerShell.")

client = genai.Client(api_key=API_KEY)

# Primary and fallback models
MODEL_LIST = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite"
]

# Separate conversation sessions for each model
chat_sessions = {}

# Voice configuration
recognizer = sr.Recognizer()
MIC_DEVICE = 1


def speak(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 160)
    engine.setProperty("volume", 1.0)

    print("\nSri:", text)

    engine.say(text)
    engine.runAndWait()
    engine.stop()

    time.sleep(0.3)


def listen():
    print("\nListening...")

    try:
        recording = sd.rec(
            int(5 * 16000),
            samplerate=16000,
            channels=1,
            dtype="int16",
            device=MIC_DEVICE
        )

        sd.wait()

        audio = sr.AudioData(recording.tobytes(), 16000, 2)

        print("Processing...")

        command = recognizer.recognize_google(audio)

        print("You:", command)

        return command.lower()

    except sr.UnknownValueError:
        print("Sri: I couldn't understand that.")
        return ""

    except sr.RequestError as error:
        print("Recognition service error:", error)
        speak("I am unable to connect to the recognition service.")
        return ""

    except Exception as error:
        print("Listening error:", error)
        return ""


def ask_gemini(question):
    for model in MODEL_LIST:
        try:
            print(f"\nSri is thinking using {model}...")

            if model not in chat_sessions:
                chat_sessions[model] = client.chats.create(
                    model=model
                )

            response = chat_sessions[model].send_message(question)

            answer = response.text

            if answer:
                speak(answer)
                return

            print("Empty response. Trying another model...")

        except Exception as error:
            print(f"{model} failed: {error}")
            print("Trying the next model...")

    speak("Both AI models are unavailable right now. Please try again later.")


def main():
    speak("Hello. I am Sri. Your personal AI assistant is ready.")

    while True:
        command = listen()

        if not command:
            continue

        # Exit commands
        if any(word in command for word in [
            "stop", "exit", "goodbye", "shut down"
        ]):
            speak("Shutting down. Goodbye.")
            break

        # Greeting
        elif command in ["hello", "hi", "hey"]:
            speak("Hello. I am listening.")

        # Assistant name
        elif "your name" in command:
            speak("My name is Sri, your personal AI assistant.")

        # Status
        elif "how are you" in command:
            speak("I am functioning perfectly. What about you?")

        # Time
        elif "time" in command:
            current_time = datetime.now().strftime("%I:%M %p")
            speak("The current time is " + current_time)

        # Date
        elif "date" in command:
            current_date = datetime.now().strftime("%d %B %Y")
            speak("Today's date is " + current_date)

        # General AI questions
        else:
            ask_gemini(command)


if __name__ == "__main__":
    main()
