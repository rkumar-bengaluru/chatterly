import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel

class LLMProviderFactory:
    @staticmethod
    def create(provider: str, model: str = None, temperature: float = 0.3, **kwargs) -> BaseChatModel:
        """
        Returns an async-compatible LangChain chat model instance.

        Supported providers:
        - "openai" → GPT-4
        - "gemini" → Gemini 2.0 Flash
        - "anthropic" → Claude Sonnet 4
        - "groq" → LLaMA 3.3 70B Versatile via api.groq.com

        Automatically pulls API keys from environment variables:
        - OPENAI_API_KEY
        - GOOGLE_API_KEY
        - ANTHROPIC_API_KEY
        - GROQ_API_KEY
        """
        provider = provider.lower()

        if provider == "openai":
            return ChatOpenAI(
                model=model or "gpt-4",
                temperature=temperature,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                streaming=False,
                **kwargs
            )

        elif provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash",
                temperature=temperature,
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                **kwargs
            )

        elif provider == "anthropic":
            return ChatAnthropic(
                model=model or "claude-sonnet-4-20250514",
                temperature=temperature,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                **kwargs
            )

        elif provider == "groq":
            return ChatGroq(
                model=model or "llama-3.3-70b-versatile",
                temperature=temperature,
                groq_api_key=os.getenv("GROQ_API_KEY"),
                **kwargs
            )

        else:
            raise ValueError(f"Unsupported provider: {provider}")
