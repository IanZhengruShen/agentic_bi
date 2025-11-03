"""
Azure OpenAI LLM Client Wrapper

This module provides a production-ready wrapper around Azure OpenAI with:
- Automatic retry logic with exponential backoff
- Token tracking and usage statistics
- Langfuse integration for observability
- Error handling and logging
- Support for chat completions with message history
"""

import asyncio
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime
import time

from openai import AsyncAzureOpenAI, AzureOpenAI
from openai import OpenAIError, RateLimitError, APITimeoutError
from pydantic import BaseModel

from app.core.config import settings

try:
    from langfuse.langchain import CallbackHandler
    from langchain_openai import AzureChatOpenAI
    LANGFUSE_AVAILABLE = True
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    LANGCHAIN_AVAILABLE = False
    CallbackHandler = None
    AzureChatOpenAI = None

logger = logging.getLogger(__name__)


class TokenUsage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    """LLM response with metadata."""

    content: str
    role: str = "assistant"
    tokens: TokenUsage
    model: str
    finish_reason: str
    latency_ms: int
    timestamp: datetime


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMClient:
    """
    Azure OpenAI client wrapper for agent operations.

    Features:
    - Async and sync operations
    - Automatic retry with exponential backoff
    - Token tracking
    - Langfuse tracing
    - Prompt/response logging
    """

    def __init__(
        self,
        langfuse_handler: Optional[CallbackHandler] = None,
        enable_langfuse: bool = True,
    ):
        """
        Initialize LLM client.

        Args:
            langfuse_handler: Optional Langfuse callback handler for tracing
            enable_langfuse: Whether to enable Langfuse tracing
        """
        self.config = settings.azure_openai
        self.enable_langfuse = enable_langfuse and LANGFUSE_AVAILABLE and settings.langfuse.langfuse_enabled
        self.langfuse_handler = langfuse_handler

        # Initialize OpenAI clients
        self._sync_client = None
        self._async_client = None
        self._langchain_client = None

        # Initialize LangChain client for Langfuse tracing if available
        if self.enable_langfuse and self.langfuse_handler and LANGCHAIN_AVAILABLE:
            try:
                self._langchain_client = AzureChatOpenAI(
                    azure_deployment=self.config.azure_openai_deployment,
                    api_version=self.config.azure_openai_api_version,
                    azure_endpoint=self.config.azure_openai_endpoint,
                    api_key=self.config.azure_openai_api_key,
                    temperature=self.config.agent_temperature,
                    max_tokens=self.config.agent_max_tokens,
                    timeout=self.config.agent_timeout,
                    model_kwargs={"response_format": {"type": "json_object"}},  # Enable JSON mode
                )
                logger.info("LangChain AzureChatOpenAI initialized for Langfuse tracing (JSON mode)")
            except Exception as e:
                logger.warning(f"Failed to initialize LangChain client: {e}")
                self._langchain_client = None

        logger.info(
            f"LLM Client initialized with model: {self.config.azure_openai_deployment}, "
            f"Langfuse: {self.enable_langfuse}, "
            f"LangChain: {self._langchain_client is not None}"
        )

    @property
    def sync_client(self) -> AzureOpenAI:
        """Get or create synchronous OpenAI client."""
        if self._sync_client is None:
            self._sync_client = AzureOpenAI(
                api_key=self.config.azure_openai_api_key,
                api_version=self.config.azure_openai_api_version,
                azure_endpoint=self.config.azure_openai_endpoint,
                timeout=self.config.agent_timeout,
            )
        return self._sync_client

    @property
    def async_client(self) -> AsyncAzureOpenAI:
        """Get or create asynchronous OpenAI client."""
        if self._async_client is None:
            self._async_client = AsyncAzureOpenAI(
                api_key=self.config.azure_openai_api_key,
                api_version=self.config.azure_openai_api_version,
                azure_endpoint=self.config.azure_openai_endpoint,
                timeout=self.config.agent_timeout,
            )
        return self._async_client

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Perform async chat completion with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            trace_name: Name for Langfuse trace
            metadata: Additional metadata for Langfuse

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMError: If completion fails after retries
        """
        temperature = temperature if temperature is not None else self.config.agent_temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.agent_max_tokens

        # Attempt with retries
        for attempt in range(self.config.agent_retry_attempts):
            try:
                start_time = time.time()

                # Prepare Langfuse metadata
                langfuse_metadata = {
                    "model": self.config.azure_openai_deployment,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "attempt": attempt + 1,
                    **(metadata or {}),
                }

                # Use LangChain client if Langfuse is enabled for automatic tracing
                if self._langchain_client and self.langfuse_handler:
                    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

                    # Convert dict messages to LangChain message objects
                    lc_messages = []
                    for msg in messages:
                        if msg["role"] == "system":
                            lc_messages.append(SystemMessage(content=msg["content"]))
                        elif msg["role"] == "user":
                            lc_messages.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant":
                            lc_messages.append(AIMessage(content=msg["content"]))

                    # Call LangChain with callback for Langfuse tracing
                    lc_response = await self._langchain_client.ainvoke(
                        lc_messages,
                        config={
                            "callbacks": [self.langfuse_handler],
                            "metadata": langfuse_metadata,
                        }
                    )

                    # Calculate latency
                    latency_ms = int((time.time() - start_time) * 1000)

                    # Extract usage info if available
                    usage_metadata = lc_response.response_metadata.get("token_usage", {})

                    # Create response object
                    llm_response = LLMResponse(
                        content=lc_response.content,
                        role="assistant",
                        tokens=TokenUsage(
                            prompt_tokens=usage_metadata.get("prompt_tokens", 0),
                            completion_tokens=usage_metadata.get("completion_tokens", 0),
                            total_tokens=usage_metadata.get("total_tokens", 0),
                        ),
                        model=self.config.azure_openai_deployment,
                        finish_reason=lc_response.response_metadata.get("finish_reason", "stop"),
                        latency_ms=latency_ms,
                        timestamp=datetime.utcnow(),
                    )

                    logger.info(
                        f"LLM completion (LangChain+Langfuse) successful: "
                        f"{llm_response.tokens.total_tokens} tokens, {latency_ms}ms latency"
                    )

                    return llm_response

                # Fallback to direct OpenAI client
                # Prepare kwargs for API call
                api_kwargs = {
                    "model": self.config.azure_openai_deployment,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                # Make API call
                response = await self.async_client.chat.completions.create(**api_kwargs)

                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)

                # Extract response data
                choice = response.choices[0]
                content = choice.message.content or ""

                # Create response object
                llm_response = LLMResponse(
                    content=content,
                    role=choice.message.role,
                    tokens=TokenUsage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    ),
                    model=response.model,
                    finish_reason=choice.finish_reason,
                    latency_ms=latency_ms,
                    timestamp=datetime.utcnow(),
                )

                # Log to Langfuse if enabled
                if self.enable_langfuse and self.langfuse_handler:
                    self._log_to_langfuse(
                        trace_name=trace_name or "llm_completion",
                        messages=messages,
                        response=llm_response,
                        metadata=langfuse_metadata,
                    )

                logger.info(
                    f"LLM completion successful: {llm_response.tokens.total_tokens} tokens, "
                    f"{latency_ms}ms latency"
                )

                return llm_response

            except RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.config.agent_retry_attempts - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise LLMError(f"Rate limit exceeded after {self.config.agent_retry_attempts} attempts") from e

            except APITimeoutError as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt < self.config.agent_retry_attempts - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise LLMError(f"Request timeout after {self.config.agent_retry_attempts} attempts") from e

            except OpenAIError as e:
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < self.config.agent_retry_attempts - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise LLMError(f"OpenAI API error: {str(e)}") from e

            except Exception as e:
                logger.error(f"Unexpected error during LLM completion: {e}")
                raise LLMError(f"Unexpected error: {str(e)}") from e

        raise LLMError(f"Failed after {self.config.agent_retry_attempts} attempts")

    def _log_to_langfuse(
        self,
        trace_name: str,
        messages: List[Dict[str, str]],
        response: LLMResponse,
        metadata: Dict[str, Any],
    ):
        """
        Log LLM call to Langfuse.

        Note: When using langfuse.langchain.CallbackHandler with LangGraph,
        tracing is handled automatically by the callback system. This method
        is kept for backwards compatibility but does minimal work.

        Args:
            trace_name: Name for the trace
            messages: Input messages
            response: LLM response
            metadata: Additional metadata
        """
        try:
            if self.langfuse_handler:
                # LangGraph callbacks handle tracing automatically
                # Just log that we're using Langfuse
                logger.debug(f"LLM call will be traced to Langfuse: {trace_name}")
        except Exception as e:
            logger.warning(f"Failed to log to Langfuse: {e}")

    async def chat_completion_with_system(
        self,
        system_message: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Convenience method for simple system + user message completion.

        Args:
            system_message: System prompt
            user_message: User message
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            trace_name: Name for Langfuse trace
            metadata: Additional metadata

        Returns:
            LLMResponse
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            trace_name=trace_name,
            metadata=metadata,
        )

    async def generate_with_schema(
        self,
        prompt: str,
        schema: type[BaseModel],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BaseModel:
        """
        Generate structured output that conforms to a Pydantic schema.

        Uses OpenAI's JSON mode or function calling to ensure the response
        matches the provided schema.

        Args:
            prompt: User prompt for generation
            schema: Pydantic model class defining the expected structure
            temperature: Override default temperature
            max_tokens: Override default max tokens
            trace_name: Name for Langfuse trace
            metadata: Additional metadata

        Returns:
            Instance of the schema model with LLM-generated data

        Raises:
            LLMError: If generation fails or response doesn't match schema
        """
        import json
        from pydantic import ValidationError

        temperature = temperature if temperature is not None else self.config.agent_temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.agent_max_tokens

        # Build system message with schema instructions
        schema_json = schema.model_json_schema()
        system_message = f"""You are a helpful assistant that generates structured JSON responses.
You must respond with valid JSON that matches this exact schema:

{json.dumps(schema_json, indent=2)}

Important:
- Return ONLY valid JSON, no additional text
- Follow the schema exactly
- Use proper data types
- Include all required fields
"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

        # Attempt with retries
        for attempt in range(self.config.agent_retry_attempts):
            try:
                start_time = time.time()

                # Use LangChain client if Langfuse is enabled for automatic tracing
                if self._langchain_client and self.langfuse_handler:
                    from langchain_core.messages import HumanMessage, SystemMessage

                    # Create LangChain messages
                    lc_messages = [
                        SystemMessage(content=system_message),
                        HumanMessage(content=prompt),
                    ]

                    # Use JSON mode instead of structured output to avoid API version issues
                    # We'll manually parse and validate
                    response = await self._langchain_client.ainvoke(
                        lc_messages,
                        config={
                            "callbacks": [self.langfuse_handler],
                            "metadata": {
                                "schema": schema.__name__,
                                "attempt": attempt + 1,
                                **(metadata or {}),
                            },
                        }
                    )

                    latency_ms = int((time.time() - start_time) * 1000)

                    # Parse and validate the JSON response
                    try:
                        json_data = json.loads(response.content)
                        validated_result = schema(**json_data)

                        logger.info(
                            f"Structured generation (LangChain+Langfuse) successful: {latency_ms}ms latency"
                        )

                        return validated_result

                    except (json.JSONDecodeError, ValidationError) as e:
                        logger.warning(f"Schema validation failed on attempt {attempt + 1}: {e}")
                        if attempt < self.config.agent_retry_attempts - 1:
                            continue
                        raise LLMError(f"Failed to generate valid structured output: {str(e)}") from e

                # Fallback to direct OpenAI client
                # Use JSON mode for structured output
                response = await self.async_client.chat.completions.create(
                    model=self.config.azure_openai_deployment,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},  # Force JSON output
                )

                latency_ms = int((time.time() - start_time) * 1000)
                choice = response.choices[0]
                content = choice.message.content or "{}"

                # Parse and validate against schema
                try:
                    json_data = json.loads(content)
                    validated_result = schema(**json_data)

                    logger.info(
                        f"Structured generation successful: {response.usage.total_tokens} tokens, "
                        f"{latency_ms}ms latency"
                    )

                    return validated_result

                except (json.JSONDecodeError, ValidationError) as e:
                    logger.warning(f"Schema validation failed on attempt {attempt + 1}: {e}")
                    if attempt < self.config.agent_retry_attempts - 1:
                        # Retry with more explicit instructions
                        continue
                    raise LLMError(f"Failed to generate valid structured output: {str(e)}") from e

            except RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.config.agent_retry_attempts - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise LLMError(f"Rate limit exceeded after {self.config.agent_retry_attempts} attempts") from e

            except APITimeoutError as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt < self.config.agent_retry_attempts - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise LLMError(f"Request timeout after {self.config.agent_retry_attempts} attempts") from e

            except OpenAIError as e:
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < self.config.agent_retry_attempts - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise LLMError(f"OpenAI API error: {str(e)}") from e

            except Exception as e:
                logger.error(f"Unexpected error during structured generation: {e}")
                raise LLMError(f"Unexpected error: {str(e)}") from e

        raise LLMError(f"Failed after {self.config.agent_retry_attempts} attempts")

    def close(self):
        """Close the clients and cleanup resources."""
        if self._sync_client:
            self._sync_client.close()
        if self._async_client:
            # AsyncAzureOpenAI doesn't have explicit close in some versions
            pass
        logger.info("LLM Client closed")


def create_llm_client(
    langfuse_handler: Optional[CallbackHandler] = None,
    enable_langfuse: bool = True,
) -> LLMClient:
    """
    Factory function to create LLM client.

    Args:
        langfuse_handler: Optional Langfuse callback handler
        enable_langfuse: Whether to enable Langfuse tracing

    Returns:
        Configured LLM client instance
    """
    return LLMClient(
        langfuse_handler=langfuse_handler,
        enable_langfuse=enable_langfuse,
    )
