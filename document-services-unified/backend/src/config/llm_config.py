import os
import asyncio
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI


async def _init_chat_model_async(model: str, model_provider: str, temperature: float, api_key: str):
    return await asyncio.to_thread(
        init_chat_model,
        model=model,
        model_provider=model_provider,
        temperature=temperature,
        api_key=api_key
    )


async def _init_google_genai_async(model: str, temperature: float, api_key: str):
    return await asyncio.to_thread(
        lambda: ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )
    )


async def get_llm(model_name: str, model_provider: str, temperature: float, structured_schema: type = None):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")

    if model_provider == "google_genai":
        llm = await _init_google_genai_async(
            model=model_name,
            temperature=temperature,
            api_key=api_key
        )
    else:
        llm = await _init_chat_model_async(
            model=model_name,
            model_provider=model_provider,
            temperature=temperature,
            api_key=api_key
        )

    if structured_schema:
        return await asyncio.to_thread(llm.with_structured_output, structured_schema)
    return llm
