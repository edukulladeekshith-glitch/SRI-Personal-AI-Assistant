
import pyttsx3
import time

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 160)
    engine.setProperty("volume", 1.0)

    print("Sri:", text)
    engine.say(text)
    engine.runAndWait()
    engine.stop()
    time.sleep(0.3)

speak("Hello. I am Sri. Your personal assistant is ready.")
speak("Voice output is working successfully.")
