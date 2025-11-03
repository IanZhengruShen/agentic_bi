"""
Tests for Combined Azure OpenAI + Langfuse POC

These tests validate the end-to-end integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add pocs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pocs"))

from combined_llm_langfuse_poc import (
    load_config,
    verify_llm_with_langfuse,
    verify_multiple_calls_with_tracing,
)


class TestCombinedLLMLangfusePOC:
    """Test suite for combined Azure OpenAI + Langfuse POC."""

    def test_load_config_missing_azure_values(self):
        """Test that load_config raises error when Azure config is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Missing Azure OpenAI configuration"):
                load_config()

    def test_load_config_missing_langfuse_values(self):
        """Test that load_config raises error when Langfuse config is missing."""
        test_env = {
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
        }

        with patch.dict("os.environ", test_env):
            with pytest.raises(ValueError, match="Missing or invalid Langfuse configuration"):
                load_config()

    def test_load_config_success(self):
        """Test successful configuration loading."""
        test_env = {
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
            "AZURE_OPENAI_API_VERSION": "2023-05-15",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-real",
            "LANGFUSE_SECRET_KEY": "sk-lf-real",
            "LANGFUSE_HOST": "https://cloud.langfuse.com",
        }

        with patch.dict("os.environ", test_env):
            config = load_config()
            assert config["azure_api_key"] == "test-key"
            assert config["langfuse_public_key"] == "pk-lf-real"

    @patch("combined_llm_langfuse_poc.CallbackHandler")
    @patch("combined_llm_langfuse_poc.AzureChatOpenAI")
    def test_llm_with_langfuse_success(self, mock_llm_class, mock_handler_class):
        """Test successful LLM call with Langfuse tracing."""
        # Mock Langfuse handler
        mock_trace = Mock()
        mock_trace.get_trace_url.return_value = "https://cloud.langfuse.com/trace/789"

        mock_handler = Mock()
        mock_handler.trace = mock_trace
        mock_handler_class.return_value = mock_handler

        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Business intelligence is the analysis of data to make better decisions."

        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        config = {
            "azure_api_key": "test-key",
            "azure_endpoint": "https://test.openai.azure.com/",
            "azure_deployment": "gpt-4",
            "azure_api_version": "2023-05-15",
            "langfuse_public_key": "pk-lf-test",
            "langfuse_secret_key": "sk-lf-test",
            "langfuse_host": "https://cloud.langfuse.com",
        }

        result = verify_llm_with_langfuse(config)

        assert result["success"] is True
        assert "Business intelligence" in result["response"]
        assert result["trace_url"] == "https://cloud.langfuse.com/trace/789"
        assert result["error"] is None
        mock_handler.flush.assert_called_once()

    @patch("combined_llm_langfuse_poc.CallbackHandler")
    @patch("combined_llm_langfuse_poc.AzureChatOpenAI")
    def test_llm_with_langfuse_failure(self, mock_llm_class, mock_handler_class):
        """Test LLM call failure handling."""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM call failed")
        mock_llm_class.return_value = mock_llm

        config = {
            "azure_api_key": "test-key",
            "azure_endpoint": "https://test.openai.azure.com/",
            "azure_deployment": "gpt-4",
            "azure_api_version": "2023-05-15",
            "langfuse_public_key": "pk-lf-test",
            "langfuse_secret_key": "sk-lf-test",
            "langfuse_host": "https://cloud.langfuse.com",
        }

        result = verify_llm_with_langfuse(config)

        assert result["success"] is False
        assert result["response"] is None
        assert "LLM call failed" in result["error"]

    @patch("combined_llm_langfuse_poc.CallbackHandler")
    @patch("combined_llm_langfuse_poc.AzureChatOpenAI")
    def test_multiple_calls_with_tracing_success(self, mock_llm_class, mock_handler_class):
        """Test multiple LLM calls in one session."""
        # Mock Langfuse handler
        mock_trace = Mock()
        mock_trace.get_trace_url.return_value = "https://cloud.langfuse.com/trace/multi"

        mock_handler = Mock()
        mock_handler.trace = mock_trace
        mock_handler_class.return_value = mock_handler

        # Mock LLM responses
        responses = [
            "SQL is a database query language.",
            "A database stores structured data.",
            "Data analysis examines data patterns.",
        ]

        mock_llm = Mock()
        mock_llm.invoke.side_effect = [Mock(content=r) for r in responses]
        mock_llm_class.return_value = mock_llm

        config = {
            "azure_api_key": "test-key",
            "azure_endpoint": "https://test.openai.azure.com/",
            "azure_deployment": "gpt-4",
            "azure_api_version": "2023-05-15",
            "langfuse_public_key": "pk-lf-test",
            "langfuse_secret_key": "sk-lf-test",
            "langfuse_host": "https://cloud.langfuse.com",
        }

        result = verify_multiple_calls_with_tracing(config)

        assert result["success"] is True
        assert len(result["responses"]) == 3
        assert result["responses"][0]["query"] == "What is SQL?"
        assert "SQL" in result["responses"][0]["response"]
        assert result["trace_url"] == "https://cloud.langfuse.com/trace/multi"
        assert result["error"] is None
        mock_handler.flush.assert_called_once()
