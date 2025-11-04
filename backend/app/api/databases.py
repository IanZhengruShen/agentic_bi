"""
Database API endpoints.

Provides endpoints for fetching accessible databases and creating new database connections.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import logging

from app.api.deps import get_current_user
from app.services.database_service import DatabaseService
from app.services.mindsdb_service import MindsDBService
from app.services.opa_client import OPAClient
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/databases", tags=["databases"])


class DatabaseInfo(BaseModel):
    """Database information."""
    name: str = Field(..., description="Database identifier (e.g., 'sales_db')")
    display_name: str = Field(..., description="Human-readable name (e.g., 'Sales Database')")
    engine: str = Field(default="unknown", description="Database engine type (e.g., 'postgres', 'mysql')")
    description: str = Field(default="", description="Optional database description")


class DatabaseListResponse(BaseModel):
    """Response for database list."""
    databases: List[DatabaseInfo] = Field(..., description="List of accessible databases")
    total_count: int = Field(..., description="Total number of accessible databases")


class DatabaseCreateRequest(BaseModel):
    """Request body for creating a database connection."""
    name: str = Field(..., description="Database connection name (unique identifier)")
    engine: str = Field(..., description="Database engine (postgres, mysql, mariadb, mongodb, etc.)")
    parameters: Dict[str, Any] = Field(..., description="Connection parameters (host, port, user, password, database, etc.)")
    display_name: Optional[str] = Field(None, description="Optional human-readable name")
    description: Optional[str] = Field(None, description="Optional description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my_postgres_db",
                "engine": "postgres",
                "display_name": "My PostgreSQL Database",
                "description": "Production database for sales data",
                "parameters": {
                    "host": "localhost",
                    "port": "5432",
                    "user": "admin",
                    "password": "secret123",
                    "database": "sales_data"
                }
            }
        }


class DatabaseCreateResponse(BaseModel):
    """Response for database creation."""
    success: bool = Field(..., description="Whether the database was created successfully")
    database_name: str = Field(..., description="Name of the created database")
    message: str = Field(..., description="Success or error message")
    error: Optional[str] = Field(None, description="Error details if failed")


@router.get("/", response_model=DatabaseListResponse)
async def get_accessible_databases(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of databases accessible to current user.

    **Flow**:
    1. Fetches all databases from MindsDB
    2. Filters by user permissions via OPA authorization
    3. Returns only databases user can access

    **Authorization**: Requires valid JWT token

    **Returns**:
    - `databases`: List of database objects with name, display_name, engine, description
    - `total_count`: Number of accessible databases

    **Example Response**:
    ```json
    {
        "databases": [
            {
                "name": "sales_db",
                "display_name": "Sales Database",
                "engine": "postgres",
                "description": "Sales data warehouse"
            },
            {
                "name": "marketing_db",
                "display_name": "Marketing Database",
                "engine": "mysql",
                "description": "Marketing campaign data"
            }
        ],
        "total_count": 2
    }
    ```

    **Error Cases**:
    - 401: Unauthorized (invalid or missing JWT token)
    - 500: Internal server error (MindsDB or OPA unavailable)
    """
    try:
        # Initialize services
        mindsdb_service = MindsDBService()
        opa_client = OPAClient()
        database_service = DatabaseService(mindsdb_service, opa_client)

        # Fetch accessible databases
        databases = await database_service.get_accessible_databases(
            user_id=str(current_user.id),
            company_id=str(current_user.company_id) if current_user.company_id else None,
            role=current_user.role
        )

        # Close MindsDB client
        await mindsdb_service.close()

        return DatabaseListResponse(
            databases=[DatabaseInfo(**db) for db in databases],
            total_count=len(databases)
        )

    except Exception as e:
        # Log error but return graceful response
        # This prevents UI from breaking if services are down
        logger.error(f"Failed to fetch databases for user {current_user.id}: {e}", exc_info=True)

        # Return empty list instead of raising error
        # This allows users to still use the chat interface
        return DatabaseListResponse(
            databases=[],
            total_count=0
        )


@router.post("/", response_model=DatabaseCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_database_connection(
    request: DatabaseCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new database connection in MindsDB.

    **Authorization**:
    - Requires valid JWT token
    - Requires "create" permission on "database" resource via OPA
    - Typically only admins can create database connections

    **Request Body**:
    ```json
    {
        "name": "my_postgres_db",
        "engine": "postgres",
        "display_name": "My PostgreSQL Database",
        "description": "Production sales database",
        "parameters": {
            "host": "localhost",
            "port": "5432",
            "user": "admin",
            "password": "secret123",
            "database": "sales_data"
        }
    }
    ```

    **Supported Engines**:
    - `postgres`: PostgreSQL
    - `mysql`: MySQL
    - `mariadb`: MariaDB
    - `mongodb`: MongoDB
    - `mssql`: Microsoft SQL Server
    - `oracle`: Oracle Database
    - `snowflake`: Snowflake
    - `bigquery`: Google BigQuery
    - And many more...

    **Example Response (Success)**:
    ```json
    {
        "success": true,
        "database_name": "my_postgres_db",
        "message": "Database connection 'my_postgres_db' created successfully"
    }
    ```

    **Example Response (Exists)**:
    ```json
    {
        "success": false,
        "database_name": "my_postgres_db",
        "message": "Database connection 'my_postgres_db' already exists",
        "error": "Database already exists"
    }
    ```

    **Error Cases**:
    - 401: Unauthorized (invalid or missing JWT token)
    - 403: Forbidden (user doesn't have permission to create databases)
    - 409: Conflict (database with same name already exists)
    - 500: Internal server error (MindsDB unavailable or connection failed)
    """
    try:
        # Check authorization via OPA
        opa_client = OPAClient()
        has_permission = await opa_client.check_permission(
            user_id=str(current_user.id),
            company_id=str(current_user.company_id) if current_user.company_id else None,
            role=current_user.role,
            action="create",
            resource_type="database",
            resource_data={"database_name": request.name, "engine": request.engine}
        )

        if not has_permission:
            logger.warning(
                f"User {current_user.id} (role: {current_user.role}) denied permission to create database '{request.name}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to create database connections"
            )

        # Create database connection via MindsDB
        mindsdb_service = MindsDBService()

        result = await mindsdb_service.create_database(
            name=request.name,
            engine=request.engine,
            parameters=request.parameters
        )

        # Close MindsDB client
        await mindsdb_service.close()

        # Return result
        if result["success"]:
            logger.info(
                f"User {current_user.id} successfully created database connection '{request.name}'"
            )
            return DatabaseCreateResponse(**result)
        else:
            # Database already exists (HTTP 409)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result.get("message", "Database already exists")
            )

    except HTTPException:
        # Re-raise HTTP exceptions (403, 409, etc.)
        raise

    except Exception as e:
        logger.error(
            f"Failed to create database '{request.name}' for user {current_user.id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create database connection: {str(e)}"
        )
