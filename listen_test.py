
import sounddevice as sd
import speech_recognition as sr
import speech_recognition.audio as sr_audio

# Directly specify the installed FLAC executable
FLAC_PATH = r"C:\Users\EDUKULLA DEEKSHITH\AppData\Local\Microsoft\WinGet\Packages\Xiph.FLAC_Microsoft.Winget.Source_8wekyb3d8bbwe\flac-1.5.0-win\Win64\flac.exe"

# Bypass SpeechRecognition's ARM64 detection problem
sr_audio.get_flac_converter = lambda: FLAC_PATH

recognizer = sr.Recognizer()

print("Sri is listening... Speak now.")

try:
    recording = sd.rec(
        int(5 * 16000),
        samplerate=16000,
        channels=1,
        dtype="int16",
        device=1
    )

    sd.wait()

    audio = sr.AudioData(recording.tobytes(), 16000, 2)

    print("Processing your voice...")

    text = recognizer.recognize_google(audio)

    print("You said:", text)

except sr.UnknownValueError:
    print("Sri could not understand your voice.")

except sr.RequestError as e:
    print("Recognition service error:", e)

except Exception as e:
    print("Error:", e)
