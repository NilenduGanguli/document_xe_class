import os
from google import genai

def get_llm():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")

    client = genai.Client(api_key=api_key)
    return client
