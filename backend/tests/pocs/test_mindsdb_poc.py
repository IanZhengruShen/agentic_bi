"""
Tests for MindsDB POC

These tests validate the MindsDB client integration functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add pocs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pocs"))

from mindsdb_poc import load_config, MindsDBClient, verify_mindsdb_connection


class TestMindsDBPOC:
    """Test suite for MindsDB POC."""

    def test_load_config_missing_values(self):
        """Test that load_config raises error when configuration is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Missing required configuration"):
                load_config()

    def test_load_config_success(self):
        """Test successful configuration loading."""
        test_env = {
            "MINDSDB_API_URL": "https://test.mindsdb.com",
        }

        with patch.dict("os.environ", test_env):
            config = load_config()
            assert config["api_url"] == "https://test.mindsdb.com"

    def test_load_config_trailing_slash_removed(self):
        """Test that trailing slash is removed from API URL."""
        test_env = {
            "MINDSDB_API_URL": "https://test.mindsdb.com/",
        }

        with patch.dict("os.environ", test_env):
            config = load_config()
            assert config["api_url"] == "https://test.mindsdb.com"

    @patch("mindsdb_poc.httpx.Client")
    def test_mindsdb_client_execute_query_success(self, mock_client_class):
        """Test successful query execution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"column1": "value1"}, {"column1": "value2"}]
        }

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = MindsDBClient("https://test.mindsdb.com")
        result = client.execute_query("SELECT * FROM test")

        assert result["success"] is True
        assert len(result["data"]) == 2
        assert result["error"] is None

    @patch("mindsdb_poc.httpx.Client")
    def test_mindsdb_client_execute_query_failure(self, mock_client_class):
        """Test query execution failure handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = MindsDBClient("https://test.mindsdb.com")
        result = client.execute_query("SELECT * FROM test")

        assert result["success"] is False
        assert result["data"] is None
        assert "HTTP 500" in result["error"]

    @patch("mindsdb_poc.httpx.Client")
    def test_mindsdb_client_health_check(self, mock_client_class):
        """Test health check functionality."""
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = MindsDBClient("https://test.mindsdb.com")
        result = client.health_check()

        assert result is True

    @patch("mindsdb_poc.MindsDBClient")
    def test_mindsdb_connection_success(self, mock_client_class):
        """Test successful MindsDB connection test."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.health_check.return_value = True
        mock_client.get_databases.return_value = {
            "success": True,
            "databases": ["mindsdb", "files"]
        }
        mock_client.get_tables.return_value = {
            "success": True,
            "tables": ["models", "predictors"]
        }
        mock_client_class.return_value = mock_client

        config = {"api_url": "https://test.mindsdb.com"}
        result = verify_mindsdb_connection(config)

        assert result["health_check"] is True
        assert "mindsdb" in result["databases"]
        assert result["tables"] is not None
        assert result["error"] is None
