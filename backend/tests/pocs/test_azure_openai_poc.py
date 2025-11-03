"""
Tests for Azure OpenAI POC

These tests validate the Azure OpenAI integration functionality.
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add pocs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pocs"))

from azure_openai_poc import load_config, verify_azure_openai_connection


class TestAzureOpenAIPOC:
    """Test suite for Azure OpenAI POC."""

    def test_load_config_missing_values(self):
        """Test that load_config raises error when configuration is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Missing required configuration"):
                load_config()

    def test_load_config_success(self):
        """Test successful configuration loading."""
        test_env = {
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
            "AZURE_OPENAI_API_VERSION": "2023-05-15",
        }

        with patch.dict("os.environ", test_env):
            config = load_config()
            assert config["api_key"] == "test-key"
            assert config["endpoint"] == "https://test.openai.azure.com/"
            assert config["deployment"] == "gpt-4"
            assert config["api_version"] == "2023-05-15"

    @patch("azure_openai_poc.AzureOpenAI")
    def test_azure_openai_connection_success(self, mock_client_class):
        """Test successful Azure OpenAI connection."""
        # Mock the response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Hello from Azure OpenAI!"))]
        mock_response.usage = Mock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_class.return_value = mock_client

        config = {
            "api_key": "test-key",
            "endpoint": "https://test.openai.azure.com/",
            "deployment": "gpt-4",
            "api_version": "2023-05-15",
        }

        result = verify_azure_openai_connection(config)

        assert result["success"] is True
        assert result["response"] == "Hello from Azure OpenAI!"
        assert result["tokens"]["prompt_tokens"] == 10
        assert result["tokens"]["completion_tokens"] == 5
        assert result["tokens"]["total_tokens"] == 15
        assert result["error"] is None

    @patch("azure_openai_poc.AzureOpenAI")
    def test_azure_openai_connection_failure(self, mock_client_class):
        """Test Azure OpenAI connection failure handling."""
        # Mock an error
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        config = {
            "api_key": "test-key",
            "endpoint": "https://test.openai.azure.com/",
            "deployment": "gpt-4",
            "api_version": "2023-05-15",
        }

        result = verify_azure_openai_connection(config)

        assert result["success"] is False
        assert result["response"] is None
        assert result["tokens"] is None
        assert "Connection failed" in result["error"]
