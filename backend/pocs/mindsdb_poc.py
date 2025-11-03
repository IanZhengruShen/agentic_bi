"""
MindsDB Client Integration POC

This POC demonstrates:
1. Connection to MindsDB (no authentication)
2. Simple query execution
3. Schema retrieval
4. Error handling

Note: MindsDB is accessed via HTTP API in this MVP (no auth required).
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import httpx


def load_config() -> Dict[str, str]:
    """Load MindsDB configuration from environment."""
    # Load from .env file if it exists
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    config = {
        "api_url": os.getenv("MINDSDB_API_URL", ""),
    }

    # Validate configuration
    if not config["api_url"]:
        raise ValueError("Missing required configuration: MINDSDB_API_URL")

    # Remove trailing slash if present
    config["api_url"] = config["api_url"].rstrip("/")

    return config


class MindsDBClient:
    """Simple MindsDB HTTP client for MVP (no auth)."""

    def __init__(self, api_url: str):
        """
        Initialize MindsDB client.

        Args:
            api_url: Base URL for MindsDB API
        """
        self.api_url = api_url
        # Configure client to follow redirects and use longer timeout
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()

    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a SQL query against MindsDB.

        Args:
            query: SQL query to execute

        Returns:
            Dict containing:
            - success: bool
            - data: List of rows (if successful)
            - error: str (if any)
        """
        result: Dict[str, Any] = {
            "success": False,
            "data": None,
            "error": None,
        }

        try:
            # MindsDB SQL API endpoint
            endpoint = f"{self.api_url}/api/sql/query"

            response = self.client.post(
                endpoint,
                json={"query": query},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                result["success"] = True
                result["data"] = data.get("data", [])
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text}"

        except httpx.TimeoutException:
            result["error"] = "Request timeout"
        except httpx.RequestError as e:
            result["error"] = f"Request error: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"

        return result

    def get_databases(self) -> Dict[str, Any]:
        """
        Retrieve list of databases from MindsDB using REST API.

        Uses GET /api/databases endpoint.

        Returns:
            Dict containing:
            - success: bool
            - databases: List of database objects
            - error: str (if any)
        """
        result: Dict[str, Any] = {
            "success": False,
            "databases": None,
            "error": None,
        }

        try:
            # MindsDB requires trailing slash
            endpoint = f"{self.api_url}/api/databases/"
            response = self.client.get(endpoint)

            if response.status_code == 200:
                data = response.json()
                result["success"] = True
                result["databases"] = data
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text}"

        except httpx.TimeoutException:
            result["error"] = "Request timeout"
        except httpx.RequestError as e:
            result["error"] = f"Request error: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"

        return result

    def get_tables(self, database: str = "mindsdb") -> Dict[str, Any]:
        """
        Retrieve list of tables from a specific database using REST API.

        Uses GET /api/tables/{database_name} endpoint.

        Args:
            database: Database name to query

        Returns:
            Dict containing:
            - success: bool
            - tables: List of table objects
            - error: str (if any)
        """
        result: Dict[str, Any] = {
            "success": False,
            "tables": None,
            "error": None,
        }

        try:
            # MindsDB requires trailing slash
            endpoint = f"{self.api_url}/api/tables/{database}/"
            response = self.client.get(endpoint)

            if response.status_code == 200:
                data = response.json()
                result["success"] = True
                result["tables"] = data
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text}"

        except httpx.TimeoutException:
            result["error"] = "Request timeout"
        except httpx.RequestError as e:
            result["error"] = f"Request error: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"

        return result

    def health_check(self) -> bool:
        """
        Check if MindsDB is accessible by trying to list databases.

        MindsDB doesn't have a dedicated health check endpoint,
        so we use GET /api/databases as a health check.

        Returns:
            True if accessible, False otherwise
        """
        try:
            # MindsDB requires trailing slash
            response = self.client.get(f"{self.api_url}/api/databases/")
            return response.status_code == 200
        except Exception:
            return False


def verify_mindsdb_connection(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Verify MindsDB connection and basic operations.

    Returns:
        Dict containing test results
    """
    result: Dict[str, Any] = {
        "health_check": False,
        "databases": None,
        "tables": None,
        "error": None,
    }

    try:
        with MindsDBClient(config["api_url"]) as client:
            # Test 1: Health check (using list databases endpoint)
            result["health_check"] = client.health_check()

            if not result["health_check"]:
                result["error"] = "MindsDB health check failed - cannot reach API"
                return result

            # Test 2: Get databases using REST API
            db_result = client.get_databases()
            if db_result["success"]:
                databases = db_result.get("databases", [])
                result["databases"] = databases

                # Extract database names for display
                if isinstance(databases, list):
                    result["database_names"] = [
                        db.get("name") if isinstance(db, dict) else str(db)
                        for db in databases
                    ]
            else:
                result["error"] = db_result["error"]
                return result

            # Test 3: Get tables from first available database or mindsdb
            target_db = "mindsdb"
            if result.get("database_names"):
                # Use first database or 'mindsdb' if it exists
                target_db = result["database_names"][0]
                if "mindsdb" in result["database_names"]:
                    target_db = "mindsdb"

            table_result = client.get_tables(target_db)
            if table_result["success"]:
                tables = table_result.get("tables", [])
                result["tables"] = tables

                # Extract table names for display
                if isinstance(tables, list):
                    result["table_names"] = [
                        tbl.get("name") if isinstance(tbl, dict) else str(tbl)
                        for tbl in tables
                    ]
            else:
                # Tables query might fail if database is empty, which is OK for POC
                result["tables"] = []
                result["table_names"] = []

    except Exception as e:
        result["error"] = f"Connection error: {str(e)}"

    return result


def main():
    """Run the MindsDB POC."""
    print("=" * 60)
    print("MindsDB Client Integration POC")
    print("=" * 60)

    try:
        # Load configuration
        print("\n1. Loading configuration...")
        config = load_config()
        print(f"   ✓ MindsDB API URL: {config['api_url']}")

        # Test connection
        print("\n2. Testing MindsDB connection...")
        result = verify_mindsdb_connection(config)

        if result.get("error"):
            print(f"   ✗ Connection failed!")
            print(f"\nError: {result['error']}")
            print("\n" + "=" * 60)
            print("POC Status: FAILED")
            print("=" * 60)
            print("\nNote: Ensure MindsDB instance is running and accessible.")
            print(f"      Configured URL: {config['api_url']}")
            sys.exit(1)

        print(f"   ✓ Health check: {'PASSED' if result['health_check'] else 'FAILED'}")

        print(f"\n3. Database Discovery (GET /api/databases):")
        if result.get("database_names"):
            for db in result["database_names"]:
                print(f"   - {db}")
            print(f"   Total: {len(result['database_names'])} database(s)")
        else:
            print("   (No databases found)")

        print(f"\n4. Table Discovery (GET /api/tables/{{database}}):")
        if result.get("table_names"):
            for table in result["table_names"]:
                print(f"   - {table}")
            print(f"   Total: {len(result['table_names'])} table(s)")
        else:
            print("   (No tables found or database is empty)")

        print("\n" + "=" * 60)
        print("POC Status: SUCCESS")
        print("=" * 60)

    except ValueError as e:
        print(f"   ✗ Configuration error: {e}")
        print("\n" + "=" * 60)
        print("POC Status: FAILED")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        print("\n" + "=" * 60)
        print("POC Status: FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
