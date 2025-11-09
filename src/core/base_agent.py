"""Base agent interface and utilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from .config import AgentConfig, LLMConfig, LLMProvider
import openai
import google.generativeai as genai
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """Result from retrieval system."""
    chunk_text: str
    score: float
    chunk_id: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AgentOutput:
    """Structured output from an agent."""
    content: str
    citations: List[str] = None
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.citations is None:
            self.citations = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AgentContext:
    """Context passed to agents."""
    player_command: str
    session_state: Dict[str, Any]
    retrieval_results: List[RetrievalResult]
    previous_turns: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.previous_turns is None:
            self.previous_turns = []


class LLMClient:
    """Abstraction layer for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client."""
        self.client = None
        match self.config.provider:
            case LLMProvider.OPENAI:
                if not self.config.api_key:
                    raise ValueError("OpenAI API key not provided")
                self.client = openai.OpenAI(api_key=self.config.api_key)
            case LLMProvider.GEMINI:
                if not self.config.api_key:
                    raise ValueError("Gemini API key not provided")
                genai.configure(api_key=self.config.api_key)
                self.client = genai.GenerativeModel(self.config.model)
            case LLMProvider.OLLAMA:
                # Ollama uses OpenAI-compatible API
                # Use "ollama" as placeholder API key (Ollama doesn't require auth)
                base_url = self.config.base_url or "http://localhost:11434/v1"
                self.client = openai.OpenAI(
                    api_key="ollama",  # Placeholder, not actually used by Ollama
                    base_url=base_url,
                )
        
        if self.client is None:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using the configured LLM."""
        try:
            if self.config.provider == LLMProvider.OPENAI:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                return response.choices[0].message.content
            
            elif self.config.provider == LLMProvider.GEMINI:
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                
                response = self.client.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_tokens,
                    ),
                )
                return response.text
            
            elif self.config.provider == LLMProvider.OLLAMA:
                # Ollama uses OpenAI-compatible API
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                return response.choices[0].message.content
            
        except Exception as e:
            logger.error("LLM generation failed", error=str(e), provider=self.config.provider)
            raise


class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        # Only initialize LLM client if enabled and config is valid
        # Ollama doesn't require API key, so check differently
        if config.enabled and config.llm:
            needs_api_key = config.llm.provider != LLMProvider.OLLAMA
            if needs_api_key and not config.llm.api_key:
                self.llm_client = None
            else:
                try:
                    self.llm_client = LLMClient(config.llm)
                except ValueError:
                    # If API key is missing, set to None and let validate_config catch it
                    self.llm_client = None
        else:
            self.llm_client = None
        self.logger = get_logger(f"agent.{config.name}")
    
    @abstractmethod
    def process(self, context: AgentContext) -> AgentOutput:
        """
        Process the context and return agent output.
        
        Args:
            context: The agent context containing player command, session state, etc.
            
        Returns:
            AgentOutput with content, citations, and metadata
        """
        pass
    
    def validate_config(self) -> bool:
        """Validate agent configuration."""
        if not self.config.enabled:
            return True
        
        if not self.config.llm:
            self.logger.error("LLM config missing")
            return False
        
        # Ollama doesn't require an API key
        if self.config.llm.provider != LLMProvider.OLLAMA:
            if not self.config.llm.api_key:
                self.logger.error("LLM API key missing")
                return False
        
        return True
    
    def format_prompt(self, template: str, **kwargs) -> str:
        """Format a prompt template with provided variables."""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            self.logger.warning(f"Missing key in prompt template: {e}")
            return template
    
    def extract_citations(self, retrieval_results: List[RetrievalResult]) -> List[str]:
        """Extract citation references from retrieval results."""
        return [f"[{i+1}]" for i in range(len(retrieval_results))]

    def test_connection(self) -> tuple[bool, Optional[str]]:
        """
        Test connection to the LLM provider.

        Returns:
            Tuple of (success, error_message)
        """
        if not self.config.enabled:
            return True, None

        if self.llm_client is None:
            return False, "LLM client not initialized"

        try:
            # Send a minimal test prompt
            test_prompt = "Hello"
            result = self.llm_client.generate(test_prompt)

            if result:
                self.logger.info(f"Connection test successful for {self.config.name}")
                return True, None
            else:
                return False, "No response from LLM"

        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

