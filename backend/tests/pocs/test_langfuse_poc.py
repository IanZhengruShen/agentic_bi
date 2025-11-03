"""
Tests for Langfuse POC

These tests validate the Langfuse integration functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add pocs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pocs"))

from langfuse_poc import load_config, verify_langfuse_connection, verify_callback_handler


class TestLangfusePOC:
    """Test suite for Langfuse POC."""

    def test_load_config_missing_values(self):
        """Test that load_config raises error when configuration is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Missing or invalid configuration"):
                load_config()

    def test_load_config_invalid_placeholder_keys(self):
        """Test that placeholder keys are rejected."""
        test_env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-xxx",
            "LANGFUSE_SECRET_KEY": "sk-lf-xxx",
            "LANGFUSE_HOST": "https://cloud.langfuse.com",
        }

        with patch.dict("os.environ", test_env):
            with pytest.raises(ValueError, match="Missing or invalid configuration"):
                load_config()

    def test_load_config_success(self):
        """Test successful configuration loading."""
        test_env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-real-key",
            "LANGFUSE_SECRET_KEY": "sk-lf-real-key",
            "LANGFUSE_HOST": "https://cloud.langfuse.com",
        }

        with patch.dict("os.environ", test_env):
            config = load_config()
            assert config["public_key"] == "pk-lf-real-key"
            assert config["secret_key"] == "sk-lf-real-key"
            assert config["host"] == "https://cloud.langfuse.com"

    @patch("langfuse_poc.Langfuse")
    def test_langfuse_connection_success(self, mock_langfuse_class):
        """Test successful Langfuse connection."""
        # Mock trace and generation
        mock_trace = Mock()
        mock_trace.get_trace_url.return_value = "https://cloud.langfuse.com/trace/123"
        mock_generation = Mock()
        mock_trace.generation.return_value = mock_generation

        mock_langfuse = Mock()
        mock_langfuse.trace.return_value = mock_trace
        mock_langfuse_class.return_value = mock_langfuse

        config = {
            "public_key": "pk-lf-test",
            "secret_key": "sk-lf-test",
            "host": "https://cloud.langfuse.com",
        }

        result = verify_langfuse_connection(config)

        assert result["success"] is True
        assert result["trace_url"] == "https://cloud.langfuse.com/trace/123"
        assert result["error"] is None
        mock_langfuse.flush.assert_called_once()

    @patch("langfuse_poc.Langfuse")
    def test_langfuse_connection_failure(self, mock_langfuse_class):
        """Test Langfuse connection failure handling."""
        mock_langfuse_class.side_effect = Exception("Authentication failed")

        config = {
            "public_key": "pk-lf-test",
            "secret_key": "sk-lf-test",
            "host": "https://cloud.langfuse.com",
        }

        result = verify_langfuse_connection(config)

        assert result["success"] is False
        assert result["trace_url"] is None
        assert "Authentication failed" in result["error"]

    @patch("langfuse_poc.CallbackHandler")
    def test_callback_handler_success(self, mock_handler_class):
        """Test successful callback handler creation."""
        mock_trace = Mock()
        mock_trace.get_trace_url.return_value = "https://cloud.langfuse.com/trace/456"

        mock_handler = Mock()
        mock_handler.trace = mock_trace
        mock_handler_class.return_value = mock_handler

        config = {
            "public_key": "pk-lf-test",
            "secret_key": "sk-lf-test",
            "host": "https://cloud.langfuse.com",
        }

        result = verify_callback_handler(config)

        assert result["success"] is True
        assert result["handler_created"] is True
        assert result["trace_url"] == "https://cloud.langfuse.com/trace/456"
        assert result["error"] is None
        mock_handler.flush.assert_called_once()

    @patch("langfuse_poc.CallbackHandler")
    def test_callback_handler_failure(self, mock_handler_class):
        """Test callback handler creation failure."""
        mock_handler_class.side_effect = Exception("Handler initialization failed")

        config = {
            "public_key": "pk-lf-test",
            "secret_key": "sk-lf-test",
            "host": "https://cloud.langfuse.com",
        }

        result = verify_callback_handler(config)

        assert result["success"] is False
        assert result["handler_created"] is False
        assert "Handler initialization failed" in result["error"]
