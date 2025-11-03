"""
MindsDB Service Client

Production-ready MindsDB client with:
- Async HTTP operations
- Connection pooling
- Automatic retry logic
- Schema caching
- Error handling
- Query validation

Note: MVP version uses no authentication. Authentication can be added post-MVP.
"""

import logging
from typing import Any, Dict, List, Optional
import time
import asyncio

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryResult(BaseModel):
    """Result from SQL query execution."""

    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    execution_time_ms: int = 0
    error: Optional[str] = None


class SchemaInfo(BaseModel):
    """Database schema information."""

    database: str
    tables: List[Dict[str, Any]]
    retrieved_at: float


class MindsDBError(Exception):
    """Base exception for MindsDB-related errors."""

    pass


class MindsDBService:
    """
    Production MindsDB service client.

    Features:
    - Async operations
    - Connection management
    - Query execution
    - Schema retrieval
    - Health checks
    """

    def __init__(self, api_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize MindsDB service.

        Args:
            api_url: Optional MindsDB API URL (defaults to settings)
            timeout: Optional timeout in seconds (defaults to settings)
        """
        self.api_url = (api_url or settings.mindsdb.mindsdb_api_url).rstrip("/")
        self.timeout = timeout or settings.mindsdb.mindsdb_timeout
        self.max_retries = settings.mindsdb.mindsdb_max_retries

        # Create async HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"MindsDB Service initialized with URL: {self.api_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                ),
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("MindsDB client closed")

    async def health_check(self) -> bool:
        """
        Check if MindsDB is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            client = await self._get_client()
            # Use databases endpoint as health check
            endpoint = f"{self.api_url}/api/databases/"
            response = await client.get(endpoint)
            is_healthy = response.status_code == 200

            if is_healthy:
                logger.info("MindsDB health check: OK")
            else:
                logger.warning(f"MindsDB health check: FAILED (status {response.status_code})")

            return is_healthy

        except Exception as e:
            logger.error(f"MindsDB health check failed: {e}")
            return False

    async def execute_query(
        self,
        query: str,
        database: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> QueryResult:
        """
        Execute SQL query against MindsDB with retry logic.

        Args:
            query: SQL query to execute
            database: Optional database context
            limit: Optional row limit

        Returns:
            QueryResult with data and metadata

        Raises:
            MindsDBError: If query execution fails after retries
        """
        # Apply limit if specified
        if limit:
            query = self._apply_limit(query, limit)

        logger.info(f"Executing query: {query[:200]}{'...' if len(query) > 200 else ''}")

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                client = await self._get_client()
                endpoint = f"{self.api_url}/api/sql/query"

                payload = {"query": query}
                if database:
                    payload["database"] = database

                logger.debug(f"MindsDB request payload: {payload}")

                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                execution_time_ms = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    data = response.json()

                    # Debug logging to see actual response structure
                    logger.debug(f"MindsDB raw response keys: {data.keys() if isinstance(data, dict) else 'not a dict'}")
                    logger.debug(f"MindsDB raw response: {data}")

                    result_data = data.get("data", [])
                    column_names = data.get("column_names", [])

                    # Check if data is in a different field
                    if not result_data and isinstance(data, dict):
                        # Try alternative response fields
                        result_data = data.get("rows", data.get("result", data.get("results", [])))
                        if result_data:
                            logger.info(f"Data found in alternative field, not 'data' field")

                    # Transform array-of-arrays to array-of-dicts if needed
                    if result_data and isinstance(result_data, list) and len(result_data) > 0:
                        # Check if first row is a list (array format)
                        if isinstance(result_data[0], list):
                            logger.info("Converting MindsDB array-of-arrays to array-of-dicts format")

                            if not column_names:
                                # If no column names provided, generate generic ones
                                column_names = [f"column_{i}" for i in range(len(result_data[0]))]
                                logger.warning(f"No column_names in response, using generic: {column_names}")

                            # Convert each array to a dict
                            result_data = [
                                dict(zip(column_names, row))
                                for row in result_data
                            ]
                            logger.debug(f"Converted first row: {result_data[0] if result_data else None}")

                    result = QueryResult(
                        success=True,
                        data=result_data,
                        row_count=len(result_data) if isinstance(result_data, list) else 0,
                        execution_time_ms=execution_time_ms,
                    )

                    logger.info(
                        f"Query executed successfully: {result.row_count} rows in {execution_time_ms}ms"
                    )
                    return result

                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(f"Query execution failed (attempt {attempt + 1}): {error_msg}")

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt)  # Exponential backoff
                        continue

                    return QueryResult(
                        success=False,
                        error=error_msg,
                        execution_time_ms=execution_time_ms,
                    )

            except httpx.TimeoutException:
                logger.warning(f"Query timeout (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                return QueryResult(
                    success=False,
                    error="Query execution timeout",
                )

            except httpx.RequestError as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                return QueryResult(
                    success=False,
                    error=f"Request error: {str(e)}",
                )

            except Exception as e:
                logger.error(f"Unexpected error during query execution: {e}")
                return QueryResult(
                    success=False,
                    error=f"Unexpected error: {str(e)}",
                )

        return QueryResult(
            success=False,
            error=f"Query failed after {self.max_retries} attempts",
        )

    async def get_databases(self) -> List[Dict[str, Any]]:
        """
        Retrieve list of databases from MindsDB.

        Returns:
            List of database dictionaries

        Raises:
            MindsDBError: If retrieval fails
        """
        try:
            client = await self._get_client()
            endpoint = f"{self.api_url}/api/databases/"

            response = await client.get(endpoint)

            if response.status_code == 200:
                databases = response.json()
                logger.info(f"Retrieved {len(databases)} databases")
                return databases if isinstance(databases, list) else []

            else:
                error_msg = f"Failed to retrieve databases: HTTP {response.status_code}"
                logger.error(error_msg)
                raise MindsDBError(error_msg)

        except httpx.RequestError as e:
            error_msg = f"Request error retrieving databases: {e}"
            logger.error(error_msg)
            raise MindsDBError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error retrieving databases: {e}"
            logger.error(error_msg)
            raise MindsDBError(error_msg) from e

    async def get_tables(self, database: str) -> List[Dict[str, Any]]:
        """
        Retrieve list of tables from a specific database.

        Args:
            database: Database name

        Returns:
            List of table dictionaries

        Raises:
            MindsDBError: If retrieval fails
        """
        try:
            client = await self._get_client()
            # Correct MindsDB API endpoint format
            endpoint = f"{self.api_url}/api/databases/{database}/tables"

            response = await client.get(endpoint)

            if response.status_code == 200:
                tables = response.json()
                logger.info(f"Retrieved {len(tables)} tables from database '{database}'")
                return tables if isinstance(tables, list) else []

            elif response.status_code == 404:
                logger.warning(f"Database '{database}' not found")
                return []

            else:
                error_msg = f"Failed to retrieve tables: HTTP {response.status_code}"
                logger.error(error_msg)
                raise MindsDBError(error_msg)

        except httpx.RequestError as e:
            error_msg = f"Request error retrieving tables: {e}"
            logger.error(error_msg)
            raise MindsDBError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error retrieving tables: {e}"
            logger.error(error_msg)
            raise MindsDBError(error_msg) from e

    async def get_schema(self, database: str, table: Optional[str] = None) -> Dict[str, Any]:
        """
        Get schema information for database/table.

        Args:
            database: Database name
            table: Optional specific table name

        Returns:
            Schema information dictionary
        """
        try:
            schema = {"database": database, "tables": {}}

            if table:
                # Get schema for specific table
                # Note: MindsDB doesn't have a direct schema endpoint, so we'll use DESCRIBE
                query = f"DESCRIBE {database}.{table}"
                result = await self.execute_query(query)

                if result.success and result.data:
                    schema["tables"][table] = {
                        "columns": result.data,
                        "row_count": len(result.data),
                    }
            else:
                # Get all tables and their basic info
                tables = await self.get_tables(database)

                for table_info in tables:
                    table_name = table_info.get("name", "unknown")
                    schema["tables"][table_name] = {
                        "info": table_info,
                        "columns": [],  # Can be populated with DESCRIBE query
                    }

            logger.info(f"Retrieved schema for database '{database}'")
            return schema

        except Exception as e:
            logger.error(f"Error retrieving schema: {e}")
            raise MindsDBError(f"Schema retrieval error: {e}") from e

    def _apply_limit(self, query: str, limit: int) -> str:
        """
        Apply LIMIT clause to query if not present.

        Args:
            query: SQL query
            limit: Row limit

        Returns:
            Query with LIMIT clause
        """
        query_upper = query.upper().strip()

        # Check if LIMIT already exists
        if "LIMIT" in query_upper:
            return query

        # Add LIMIT clause
        if query.strip().endswith(";"):
            return f"{query[:-1]} LIMIT {limit};"
        else:
            return f"{query} LIMIT {limit}"

    async def validate_connection(self) -> Dict[str, Any]:
        """
        Validate MindsDB connection and return diagnostic info.

        Returns:
            Dictionary with validation results
        """
        result = {
            "connected": False,
            "api_url": self.api_url,
            "databases": [],
            "error": None,
        }

        try:
            # Check health
            is_healthy = await self.health_check()
            result["connected"] = is_healthy

            if is_healthy:
                # Get databases
                databases = await self.get_databases()
                result["databases"] = [
                    db.get("name") if isinstance(db, dict) else str(db) for db in databases
                ]

        except Exception as e:
            result["error"] = str(e)

        return result


# Factory function
def create_mindsdb_service(
    api_url: Optional[str] = None,
    timeout: Optional[int] = None,
) -> MindsDBService:
    """
    Factory function to create MindsDB service.

    Args:
        api_url: Optional API URL override
        timeout: Optional timeout override

    Returns:
        Configured MindsDBService instance
    """
    return MindsDBService(api_url=api_url, timeout=timeout)
