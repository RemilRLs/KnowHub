from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass

class PromptType(str, Enum):
    """
    Types of prompts for different use cases.
    """
    RAG_GENERATION = "rag_generation"
    SUMMARIZATION = "summarization"
    CHAT = "chat"
    CUSTOM = "custom"

@dataclass
class PromptTemplate:
    """
    Template for a prompt with system and user components.
    """
    system: str
    user: str
    description: Optional[str] = None


class PromptBuilder:
    """
    Builds prompts based on predefined templates and user input.
    """

    # Mapping of PromptType to PromptTemplate
    TEMPLATES = {
        PromptType.RAG_GENERATION: PromptTemplate(
            system="""You are an AI assistant that answers questions strictly based on the retrieved context provided.
Do not use outside knowledge or make assumptions beyond this context.
If the context does not contain enough information to answer, clearly say so.
Always respond in a clear, concise, and professional manner.""",
            user="""Context:
{context}

Question:
{query}

Instructions:
- Use only the information from the context above.
- If the answer is not explicitly present, respond with "The provided context does not contain enough information to answer."
- Write your answer in clear, concise, and professional language.
- Do not include references to the instructions or the word 'context' in your answer.

Answer:""",
            description="RAG generation prompt for answering questions based on context"
        ),
    }


    def __init__(self, prompt_type: PromptType = PromptType.RAG_GENERATION):
        self.prompt_type = prompt_type
        self.template = self.TEMPLATES.get(prompt_type)

        self._variables = {}

    def add_variable(self, key: str, value: Any) -> "PromptBuilder":
        """
        Add a variable to be interpolated in the prompt.
        
        Args:
            key: Variable name
            value: Variable value
            
        Returns:
            Self for chaining
        """
        self._variables[key] = value
        return self
    
    def add_variables(self, **kwargs) -> "PromptBuilder":
        """
        Add multiple variables at once.
        
        Args:
            **kwargs: Variables as keyword arguments
            
        Returns:
            Self for chaining
        """
        self._variables.update(kwargs)
        return self
    
    def build_messages(self) -> List[Dict[str, str]]:
        """
        
        """

        system_prompt = self.template.system
        user_prompt_template = self.template.user
        user_prompt = user_prompt_template.format(**self._variables)

        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": user_prompt
            })
        
        return messages




