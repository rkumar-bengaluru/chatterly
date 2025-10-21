import os

class LLMProviderFactory:
    @staticmethod
    def create(provider: str, model: str = None, temperature: float = 0.3, streaming: bool = False, **kwargs) -> dict:
        """
        Returns an AutoGen-compatible llm_config dictionary.

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
            return {
                "config_list": [{
                    "model": model or "gpt-4",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "stream": streaming,
                    **kwargs
                }]
            }

        elif provider == "gemini":
            return {
                "config_list": [{
                    "model": model or "gemini-2.0-flash",
                    "api_key": os.getenv("GOOGLE_API_KEY"),
                    "api_base": "https://generativelanguage.googleapis.com",
                    "stream": streaming,
                    **kwargs
                }]
            }

        elif provider == "anthropic":
            return {
                "config_list": [{
                    "model": model or "claude-sonnet-4-20250514",
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "api_base": "https://api.anthropic.com",
                    "stream": streaming,
                    **kwargs
                }]
            }

        elif provider == "groq":
            return {
                "config_list": [{
                    "model": model or "llama3-70b-8192",
                    "api_key": os.getenv("GROQ_API_KEY"),
                    "api_base": "https://api.groq.com",
                    "stream": streaming,
                    **kwargs
                }]
            }

        else:
            raise ValueError(f"Unsupported provider: {provider}")
