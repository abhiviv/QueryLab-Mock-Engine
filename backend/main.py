import asyncio
import time
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.schemas import SandboxEnvironment, MockRouteConfig, DatabaseInspectRequest
from backend.database_inspector import extract_schema_metadata, generate_mock_records

app = FastAPI(
    title="QueryLab Mock Engine",
    description="Local high-performance mock simulation daemon featuring dynamic database inspection",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "querylab.json")

def save_config(env: SandboxEnvironment):
    try:
        data = env.model_dump() if hasattr(env, "model_dump") else env.dict()
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error persisting configuration: {e}")

def load_config() -> Optional[SandboxEnvironment]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                return SandboxEnvironment(**data)
        except Exception as e:
            print(f"Error loading configuration from disk: {e}")
    return None

# In-memory runtime stores
class RuntimeStore:
    def __init__(self):
        self.active_sandbox: Optional[SandboxEnvironment] = None
        self.schema_cache: Dict[str, List[Dict[str, Any]]] = {}  # table_name -> column_meta
        self.logs: List[Dict[str, Any]] = []
        
        # Load persisted config on boot
        loaded = load_config()
        if loaded:
            self.active_sandbox = loaded
            if loaded.table_schemas:
                self.schema_cache = loaded.table_schemas
            elif loaded.db_connection_string:
                inspect_res = extract_schema_metadata(loaded.db_connection_string)
                if inspect_res["success"]:
                    self.schema_cache = inspect_res["tables"]

store = RuntimeStore()

def add_log_entry(path: str, method: str, target_table: Optional[str], latency_ms: int, status_code: int, response_size: int):
    """Adds a trace log entry for mocked request auditing."""
    log_entry = {
        "id": f"log-{int(time.time() * 1000)}",
        "timestamp": datetime.now().isoformat(),
        "path": f"/mock/{path}",
        "method": method.upper(),
        "target_table": target_table or "None",
        "latency_ms": latency_ms,
        "status_code": status_code,
        "response_size_bytes": response_size
    }
    store.logs.insert(0, log_entry)
    # Cap log size to prevent infinite memory usage in long-running sessions
    if len(store.logs) > 100:
        store.logs.pop()

@app.post("/api/sandbox/inspect")
async def inspect_database(req: DatabaseInspectRequest):
    """
    On-the-fly database inspector endpoint.
    Retrieves and returns all tables, columns, and datatypes.
    """
    result = extract_schema_metadata(req.db_connection_string)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    return result

@app.post("/api/sandbox/register")
async def register_sandbox(env: SandboxEnvironment):
    """
    Registers a SandboxEnvironment, cache database structures, and activate mock paths.
    """
    store.active_sandbox = env
    store.schema_cache.clear()
    
    # Cache schema and custom overrides if provided by frontend, else inspect DB
    if env.table_schemas:
        store.schema_cache = env.table_schemas
    elif env.db_connection_string:
        inspect_res = extract_schema_metadata(env.db_connection_string)
        if inspect_res["success"]:
            store.schema_cache = inspect_res["tables"]
            
    save_config(env)
            
    return {
        "status": "success",
        "message": f"Sandbox environment '{env.environment_name}' registered successfully.",
        "cached_tables": list(store.schema_cache.keys())
    }

@app.get("/api/sandbox/active")
async def get_active_sandbox():
    """
    Returns current active configurations and cache tables.
    """
    return {
        "active_sandbox": store.active_sandbox,
        "cached_tables": list(store.schema_cache.keys())
    }

@app.get("/api/sandbox/logs")
async def get_mock_logs():
    """
    Returns history log of mock request interceptions.
    """
    return store.logs

@app.post("/api/sandbox/logs/clear")
async def clear_logs():
    """
    Clears mock history log.
    """
    store.logs.clear()
    return {"status": "success"}

class PreviewRequest(BaseModel):
    route: MockRouteConfig
    table_schemas: Optional[Dict[str, List[Dict[str, Any]]]] = Field(default_factory=dict)

@app.post("/api/sandbox/preview")
async def preview_route(req: PreviewRequest):
    """
    Generates a single dry-run mock response payload for dashboard live-previews.
    """
    table = req.route.target_table
    columns = req.table_schemas.get(table) if (req.table_schemas and table) else None
    
    is_single_item = (req.route.http_method in ["POST", "PUT", "DELETE"])
    
    if columns:
        records = generate_mock_records(columns, req.route.records_count)
        response_data = records[0] if (is_single_item and records) else records
    else:
        fallback_cols = [
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "name", "type": "VARCHAR"},
            {"name": "status", "type": "VARCHAR"},
            {"name": "updated_at", "type": "DATETIME"}
        ]
        records = generate_mock_records(fallback_cols, req.route.records_count)
        response_data = records[0] if is_single_item else records
        
    if req.route.http_method == "DELETE":
        response_data = {"status": "success", "message": f"Resource from table '{table or 'generic'}' deleted successfully."}
        
    return response_data

# Wildcard route interceptor matching all methods
@app.api_route("/mock/{proxy_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def intercept_mock_call(proxy_path: str, request: Request):
    start_time = time.time()
    method = request.method.upper()
    
    # Verify sandbox is active
    if not store.active_sandbox:
        add_log_entry(proxy_path, method, None, 0, 400, 0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active sandbox environment registered. Please register a sandbox via the dashboard."
        )
        
    # Match route configs (exact path or prefix check)
    matched_config: Optional[MockRouteConfig] = None
    for config in store.active_sandbox.routes:
        # Match endpoint path.
        # Handle cases where endpoint_path is 'users' and proxy_path is 'users' or 'users/5'
        conf_path = config.endpoint_path.strip("/")
        prox_path = proxy_path.strip("/")
        
        # Check if methods match and paths are compatible
        if config.http_method.upper() == method:
            if conf_path == prox_path or prox_path.startswith(conf_path + "/"):
                matched_config = config
                break
                
    if not matched_config:
        add_log_entry(proxy_path, method, None, 0, 404, 0)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock route not configured for method '{method}' on path '{proxy_path}'"
        )
        
    # Simulate Latency Delay via asyncio.sleep
    latency = matched_config.latency_ms
    if latency > 0:
        await asyncio.sleep(latency / 1000.0)
        
    # Generate dynamic mockup payload
    response_data: Any = None
    table = matched_config.target_table
    
    # Extract structural schema from cache (if table is found in db) or fallback to generic schemas
    columns = store.schema_cache.get(table) if table else None
    
    # Determine if request is requesting a single resource (e.g. proxy_path has trailing parts: users/5)
    conf_path = matched_config.endpoint_path.strip("/")
    prox_path = proxy_path.strip("/")
    is_single_item = (conf_path != prox_path) or (method in ["POST", "PUT", "DELETE"])
    
    if columns:
        # Generate schema-driven data
        records = generate_mock_records(columns, matched_config.records_count)
        if is_single_item:
            # Return single record
            response_data = records[0] if records else {}
        else:
            response_data = records
    else:
        # Fallback dynamic generic layout
        fallback_cols = [
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "name", "type": "VARCHAR"},
            {"name": "status", "type": "VARCHAR"},
            {"name": "updated_at", "type": "DATETIME"}
        ]
        records = generate_mock_records(fallback_cols, matched_config.records_count)
        if is_single_item:
            response_data = records[0]
        else:
            response_data = records
            
    # Modify ID / response values based on PUT/DELETE if applicable
    if method == "DELETE":
        response_data = {"status": "success", "message": f"Resource from table '{table or 'generic'}' deleted successfully."}
        
    actual_latency = int((time.time() - start_time) * 1000)
    
    # Calculate approximate response size in bytes
    import json
    response_bytes = len(json.dumps(response_data).encode("utf-8"))
    
    add_log_entry(proxy_path, method, table, actual_latency, 200, response_bytes)
    
    return response_data
