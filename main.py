
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

speak("Hello. I am Sri.")
speak("Your personal AI assistant.")
speak("All systems are online.")
speak("How can I help you today?")
