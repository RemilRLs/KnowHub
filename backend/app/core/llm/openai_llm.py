import logging
from typing import List, Dict, Optional
from openai import OpenAI

from app.core.generator.llmprovider import BaseLLM

logger = logging.getLogger(__name__)

class OpenAILLM(BaseLLM):
    """
    OpenAI LLM implementation.
    """
    def __init__(
            self,
            model: str = "gpt-4",
            temperature: float = 0.7,
            max_tokens: int = 2048,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            **kwargs
    ):
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generates text using vLLM OpenAI-compatible API.
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return self.generate_chat(messages, **kwargs)
    
    def generate_chat(
            self,
            messages: List[Dict[str, str]],
            **kwargs
    ) -> str:
        """
        Generates text using OpenAI Chat API with message history.
        """
        params = self._merge_params(**kwargs)

        try:
            logger.info(f"Calling OpenAI API with model '{self.model}'")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=params["temperature"],
                max_tokens=params["max_tokens"],
                **{k: v for k, v in params.items() if k not in ["temperature", "max_tokens"]}
            )
            
            answer = response.choices[0].message.content
            logger.info(f"OpenAI response received: {len(answer)} chars")
            
            return answer
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            raise