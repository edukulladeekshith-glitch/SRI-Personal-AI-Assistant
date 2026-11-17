
import sounddevice as sd

print("Sri is checking your microphone...")

devices = sd.query_devices()

for i, device in enumerate(devices):
    if device["max_input_channels"] > 0:
        print(i, device["name"])

print("\nMicrophone detection complete.")
