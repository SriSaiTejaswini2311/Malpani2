import google.generativeai as genai
import os
from dotenv import load_dotenv
from pathlib import Path

# Load env from backend/.env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("Listing supported generateContent models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"AVAILABLE: {m.name}")

print("\nTesting 'models/gemini-1.5-flash'...")
try:
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    response = model.generate_content("Hello")
    print(f"SUCCESS with prefix: {response.text}")
except Exception as e:
    print(f"FAIL with prefix: {e}")

print("\nTesting 'gemini-1.5-flash' (no prefix)...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello")
    print(f"SUCCESS no prefix: {response.text}")
except Exception as e:
    print(f"FAIL no prefix: {e}")
