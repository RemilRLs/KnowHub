from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """
    Supported LLM providers.
    """
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"

class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.
    """

    def __init__(
            self,
            model: str,
            temperature: float = 0.5,
            max_tokens: int = 2048,
            **kwargs,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_params = kwargs

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text based on the prompt.

        Args:
            prompt: The input prompt for generation.
            system_prompt: Optional system prompt for context.
            **kwargs: Additional parameters for generation.

        Returns:
            Generated text
        """

        pass


    @abstractmethod
    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Generates text based on a chat history.
        
        Args:
            messages: List of messages [{"role": "user/assistant/system", "content": "..."}]
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text
        """

        pass

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ):
        raise NotImplementedError("Streaming not supported by this provider")

    
    def _merge_params(self, **override_params) -> Dict[str, Any]:
        """
        Merges default params with override params.
        """

        params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **self.extra_params
        }
        params.update(override_params)
        return params
    
class LLMFactory:
    """
    Factory for creating LLM provider instances

    Using design pattern: https://refactoring.guru/design-patterns/factory-method/python/example
    """

    @staticmethod
    def _normalize_provider_name(provider_name: str) -> LLMProvider:
        """
        Normalizes provider name string to LLMProvider enum.
        """

        if isinstance(provider_name, LLMProvider):
            return provider_name
        s = provider_name.strip().lower()
        return LLMProvider(s)

    @staticmethod
    def create(
        provider: LLMProvider,
        model: str,
        temperature: float = 0.5,
        **kwargs,
    ) -> BaseLLM:
        """
        Creates an LLM instance for the specified provider.
        
        Args:
            provider: LLM provider
            model: Model name
            temperature: Generation temperature
            **kwargs: Provider-specific parameters
            
        Returns:
            LLM instance
        """

        from app.core.llm.openai_llm import OpenAILLM
        # from app.core.generator.llm.anthropic_llm import AnthropicLLM
        # from app.core.llm.generator.ollama_llm import OllamaLLM
        # from app.core.llm.generator.vllm_llm import VLLM

        # If the user in the .env write for example LLM_PROVIDER=openai, the OpenAILLM class will be used
        provider_enum = LLMFactory._normalize_provider_name(provider)
        providers_map = {
            LLMProvider.OPENAI: OpenAILLM,
            LLMProvider.ANTHROPIC: "AnthropicLLM",
            LLMProvider.OLLAMA: "OllamaLLM",
            LLMProvider.VLLM: "VLLM",
        }

        llm_class = providers_map.get(provider_enum) # The provider will be found thanks to the .env settings
        if not llm_class:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        return llm_class(
            model=model,
            temperature=temperature,
            **kwargs
        )