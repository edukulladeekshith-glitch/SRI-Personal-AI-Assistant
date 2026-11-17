
import os
import time
from google import genai

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Gemini API key not found.")
    raise SystemExit

client = genai.Client(api_key=api_key)

for attempt in range(3):
    try:
        print("Connecting Sri to Gemini...")

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents="Introduce yourself as the AI brain of Sri in one sentence."
        )

        print("\nSri AI:", response.text)
        break

    except Exception as e:
        print(f"Attempt {attempt + 1} failed: {e}")

        if attempt < 2:
            print("Retrying in 5 seconds...")
            time.sleep(5)
        else:
            print("Gemini connection failed. Try again later.")
