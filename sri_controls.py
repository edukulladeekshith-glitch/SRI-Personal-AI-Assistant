
import os
import subprocess
import webbrowser
import urllib.parse
import ctypes
import psutil
import re


def open_app(name):
    apps = {
        "chrome": "chrome",
        "calculator": "calc",
        "notepad": "notepad",
        "paint": "mspaint",
        "file explorer": "explorer",
        "explorer": "explorer",
        "command prompt": "cmd",
        "powershell": "powershell",
        "vscode": "code",
        "vs code": "code"
    }

    if name in apps:
        try:
            subprocess.Popen(
                f'start "" {apps[name]}',
                shell=True
            )
            return f"Opening {name}."
        except Exception:
            return f"Could not open {name}."

    return f"I don't recognize the application {name}."


def open_website(name):
    websites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
        "chatgpt": "https://chatgpt.com",
        "instagram": "https://www.instagram.com",
        "facebook": "https://www.facebook.com"
    }

    if name in websites:
        webbrowser.open(websites[name])
        return f"Opening {name}."

    return None


def google_search(query):
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Searching Google for {query}."


def volume_control(action):
    keys = {
        "up": 0xAF,
        "down": 0xAE,
        "mute": 0xAD
    }

    if action not in keys:
        return "Unknown volume command."

    ctypes.windll.user32.keybd_event(keys[action], 0, 0, 0)
    ctypes.windll.user32.keybd_event(keys[action], 0, 2, 0)

    return {
        "up": "Volume increased.",
        "down": "Volume decreased.",
        "mute": "Mute toggled."
    }[action]


def system_info():
    battery = psutil.sensors_battery()
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()

    if battery:
        battery_text = f"{battery.percent}%"
        charging = "Charging" if battery.power_plugged else "Not charging"
    else:
        battery_text = "Unavailable"
        charging = "Unknown"

    return (
        f"Battery: {battery_text}. {charging}. "
        f"CPU usage: {cpu} percent. "
        f"RAM usage: {memory.percent} percent."
    )


def open_settings(setting):
    settings = {
        "settings": "ms-settings:",
        "wifi": "ms-settings:network-wifi",
        "wi-fi": "ms-settings:network-wifi",
        "bluetooth": "ms-settings:bluetooth",
        "display": "ms-settings:display",
        "sound": "ms-settings:sound",
        "network": "ms-settings:network",
        "windows update": "ms-settings:windowsupdate"
    }

    if setting not in settings:
        return None

    os.startfile(settings[setting])
    return f"Opening {setting} settings."


def lock_laptop():
    ctypes.windll.user32.LockWorkStation()
    return "Locking your laptop."


def handle_command(command):
    command = command.lower().strip()
    command = re.sub(r"[.!?]+$", "", command)

    if command in ["open chrome", "launch chrome"]:
        return open_app("chrome")

    if command in ["open calculator", "open calc"]:
        return open_app("calculator")

    if command in ["open notepad"]:
        return open_app("notepad")

    if command in ["open paint"]:
        return open_app("paint")

    if command in ["open file explorer", "open explorer"]:
        return open_app("file explorer")

    if command in ["open vscode", "open vs code", "open visual studio code"]:
        return open_app("vs code")

    if command in ["open command prompt", "open cmd"]:
        return open_app("command prompt")

    if command.startswith("open "):
        name = command[5:].strip()
        result = open_website(name)
        if result:
            return result

    if command.startswith("search google for "):
        query = command.replace("search google for ", "", 1).strip()
        if query:
            return google_search(query)

    if command.startswith("search for "):
        query = command.replace("search for ", "", 1).strip()
        if query:
            return google_search(query)

    if "increase volume" in command or "volume up" in command:
        return volume_control("up")

    if "decrease volume" in command or "volume down" in command:
        return volume_control("down")

    if "mute" in command:
        return volume_control("mute")

    if "battery" in command or "cpu usage" in command or "ram usage" in command:
        return system_info()

    if command in ["open settings", "open windows settings"]:
        return open_settings("settings")

    if "wifi settings" in command or "wi-fi settings" in command:
        return open_settings("wifi")

    if "bluetooth settings" in command:
        return open_settings("bluetooth")

    if "display settings" in command:
        return open_settings("display")

    if "sound settings" in command:
        return open_settings("sound")

    if "network settings" in command:
        return open_settings("network")

    if "windows update" in command:
        return open_settings("windows update")

    if command in ["lock laptop", "lock my laptop", "lock computer"]:
        return lock_laptop()

    return None
