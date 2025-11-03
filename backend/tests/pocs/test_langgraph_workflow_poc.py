"""
Tests for LangGraph Workflow POC

These tests validate the LangGraph workflow integration functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add pocs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pocs"))

from langgraph_workflow_poc import load_config, create_workflow, run_workflow_poc


class TestLangGraphWorkflowPOC:
    """Test suite for LangGraph Workflow POC."""

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

    @patch("langgraph_workflow_poc.AzureChatOpenAI")
    def test_create_workflow(self, mock_llm_class):
        """Test workflow creation."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm

        mock_handler = Mock()

        config = {
            "azure_api_key": "test-key",
            "azure_endpoint": "https://test.openai.azure.com/",
            "azure_deployment": "gpt-4",
            "azure_api_version": "2023-05-15",
        }

        workflow = create_workflow(config, mock_handler)

        assert workflow is not None
        # Verify workflow has expected nodes
        assert hasattr(workflow, 'nodes')

    @patch("langgraph_workflow_poc.CallbackHandler")
    @patch("langgraph_workflow_poc.AzureChatOpenAI")
    @patch("langgraph_workflow_poc.create_workflow")
    def test_run_workflow_poc_success(self, mock_create_workflow, mock_llm_class, mock_handler_class):
        """Test successful workflow execution."""
        # Mock Langfuse handler
        mock_trace = Mock()
        mock_trace.get_trace_url.return_value = "https://cloud.langfuse.com/trace/workflow"

        mock_handler = Mock()
        mock_handler.trace = mock_trace
        mock_handler_class.return_value = mock_handler

        # Mock workflow
        mock_app = Mock()
        mock_app.invoke.return_value = {
            "query": "test query",
            "intent": "analytics",
            "sql_query": "SELECT * FROM test",
            "result": "test result",
            "error": "",
            "messages": ["step1", "step2"]
        }

        mock_workflow = Mock()
        mock_workflow.compile.return_value = mock_app
        mock_create_workflow.return_value = mock_workflow

        config = {
            "azure_api_key": "test-key",
            "azure_endpoint": "https://test.openai.azure.com/",
            "azure_deployment": "gpt-4",
            "azure_api_version": "2023-05-15",
            "langfuse_public_key": "pk-lf-test",
            "langfuse_secret_key": "sk-lf-test",
            "langfuse_host": "https://cloud.langfuse.com",
        }

        result = run_workflow_poc(config)

        assert result["success"] is True
        assert result["result"]["intent"] == "analytics"
        assert result["trace_url"] == "https://cloud.langfuse.com/trace/workflow"
        assert result["error"] is None
        mock_handler.flush.assert_called_once()

    @patch("langgraph_workflow_poc.CallbackHandler")
    def test_run_workflow_poc_failure(self, mock_handler_class):
        """Test workflow execution failure handling."""
        mock_handler_class.side_effect = Exception("Workflow failed")

        config = {
            "azure_api_key": "test-key",
            "azure_endpoint": "https://test.openai.azure.com/",
            "azure_deployment": "gpt-4",
            "azure_api_version": "2023-05-15",
            "langfuse_public_key": "pk-lf-test",
            "langfuse_secret_key": "sk-lf-test",
            "langfuse_host": "https://cloud.langfuse.com",
        }

        result = run_workflow_poc(config)

        assert result["success"] is False
        assert result["result"] is None
        assert "Workflow failed" in result["error"]
