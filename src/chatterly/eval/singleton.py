# agent_session/singleton.py

from chatterly.eval.llm_factory import LLMProviderFactory
from chatterly.eval.evaluator import ConversationEvaluator

_evaluator_instance = None  # Module-level cache

async def get_openai_evaluator(provider: str = "openai", model: str = "gpt-4", temperature: float = 0.3, **kwargs) -> ConversationEvaluator:
    """
    Returns a singleton instance of GoAnswerEvaluator for the session.

    Args:
        provider (str): LLM provider name ("openai", "gemini", "anthropic", "groq")
        model (str): Optional model name override
        temperature (float): Sampling temperature
        kwargs: Additional config passed to LLMProviderFactory

    Returns:
        GoAnswerEvaluator: Singleton evaluator instance
    """
    global _evaluator_instance

    if _evaluator_instance is None:
        llm = LLMProviderFactory.create(provider=provider, model=model, temperature=temperature, **kwargs)
       
        _evaluator_instance = ConversationEvaluator(llm)

    return _evaluator_instance

async def get_antropic_evaluator(provider: str = "anthropic", model: str = "claude-sonnet-4-20250514", temperature: float = 0.3, **kwargs) -> ConversationEvaluator:
    """
    Returns a singleton instance of GoAnswerEvaluator for the session.

    Args:
        provider (str): LLM provider name ("openai", "gemini", "anthropic", "groq")
        model (str): Optional model name override
        temperature (float): Sampling temperature
        kwargs: Additional config passed to LLMProviderFactory

    Returns:
        GoAnswerEvaluator: Singleton evaluator instance
    """
    global _evaluator_instance

    if _evaluator_instance is None:
        llm = LLMProviderFactory.create(provider=provider, model=model, temperature=temperature, **kwargs)
       
        _evaluator_instance = ConversationEvaluator(llm)

    return _evaluator_instance


async def get_llama_evaluator(provider: str = "groq", model: str = "llama-3.3-70b-versatile", temperature: float = 0.3, **kwargs) -> ConversationEvaluator:
    """
    Returns a singleton instance of GoAnswerEvaluator for the session.

    Args:
        provider (str): LLM provider name ("openai", "gemini", "anthropic", "groq")
        model (str): Optional model name override
        temperature (float): Sampling temperature
        kwargs: Additional config passed to LLMProviderFactory

    Returns:
        GoAnswerEvaluator: Singleton evaluator instance
    """
    global _evaluator_instance

    if _evaluator_instance is None:
        llm = LLMProviderFactory.create(provider=provider, model=model, temperature=temperature, **kwargs)
       
        _evaluator_instance = ConversationEvaluator(llm)

    return _evaluator_instance


async def get_gemini_evaluator(provider: str = "gemini", model: str = "gemini-2.0-flash", temperature: float = 0.3, **kwargs) -> ConversationEvaluator:
    """
    Returns a singleton instance of GoAnswerEvaluator for the session.

    Args:
        provider (str): LLM provider name ("openai", "gemini", "anthropic", "groq")
        model (str): Optional model name override
        temperature (float): Sampling temperature
        kwargs: Additional config passed to LLMProviderFactory

    Returns:
        GoAnswerEvaluator: Singleton evaluator instance
    """
    global _evaluator_instance

    if _evaluator_instance is None:
        llm = LLMProviderFactory.create(provider=provider, model=model, temperature=temperature, **kwargs)
       
        _evaluator_instance = ConversationEvaluator(llm)

    return _evaluator_instance


async def get_evaluator_singleton(provider: str = "openai", model: str = None, temperature: float = 0.3, **kwargs) -> ConversationEvaluator:
    """
    Returns a singleton instance of GoAnswerEvaluator for the session.

    Args:
        provider (str): LLM provider name ("openai", "gemini", "anthropic", "groq")
        model (str): Optional model name override
        temperature (float): Sampling temperature
        kwargs: Additional config passed to LLMProviderFactory

    Returns:
        GoAnswerEvaluator: Singleton evaluator instance
    """
    global _evaluator_instance

    if _evaluator_instance is None:
        llm = LLMProviderFactory.create(provider=provider, model=model, temperature=temperature, **kwargs)
       
        _evaluator_instance = ConversationEvaluator(llm)

    return _evaluator_instance
