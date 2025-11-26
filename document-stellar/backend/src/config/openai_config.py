import os
from openai import AsyncOpenAI

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    client = AsyncOpenAI(api_key=api_key)
    return client
