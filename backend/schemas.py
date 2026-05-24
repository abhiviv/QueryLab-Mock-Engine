from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class MockRouteConfig(BaseModel):
    endpoint_path: str = Field(..., description="The wildcard path to intercept, e.g., 'users'")
    http_method: str = Field(..., description="HTTP Method to mock, e.g., 'GET', 'POST', 'PUT', 'DELETE'")
    target_table: Optional[str] = Field(None, description="Database table name used for schema-driven mock generation")
    records_count: int = Field(5, ge=1, le=100, description="Number of mock records to generate")
    latency_ms: int = Field(200, ge=0, le=10000, description="Latency delay to simulate in milliseconds")

class SandboxEnvironment(BaseModel):
    environment_name: str = Field(..., description="Unique label for the mock sandbox environment")
    db_connection_string: Optional[str] = Field(None, description="SQLAlchemy compatible connection string (SQLite, MySQL, etc.)")
    routes: List[MockRouteConfig] = Field(default_factory=list, description="List of endpoint routing configs")
    table_schemas: Optional[Dict[str, List[Dict[str, Any]]]] = Field(default_factory=dict, description="Cached table schemas with custom overrides")

class DatabaseInspectRequest(BaseModel):
    db_connection_string: str = Field(..., description="SQLAlchemy connection URL to inspect, e.g., sqlite:///dev.db")
