from pydantic_settings import BaseSettings
from app.core.generator.llmprovider import LLMProvider

class LLMSettings(BaseSettings):
    """LLM configuration settings."""
    
    # Provider selection
    LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI
    LLM_MODEL: str = "gpt-4"
    
    # Generation parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # vLLM
    VLLM_BASE_URL: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


llm_settings = LLMSettings()