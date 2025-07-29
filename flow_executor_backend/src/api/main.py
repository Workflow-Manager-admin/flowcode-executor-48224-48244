from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import subprocess
import uuid

### --- OpenAPI/Swagger tags ---
openapi_tags = [
    {"name": "flows", "description": "Flow CRUD operations"},
    {"name": "execution", "description": "JavaScript code execution"},
    {"name": "results", "description": "Execution result management"},
]

app = FastAPI(
    title="Flow Diagram-Based JavaScript Code Executor Backend",
    description="Backend for Visual Flow Diagram JS Executor. Allows JS code execution, flow CRUD, and result management.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adapt for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#########################################
# --- Pydantic Models ---
#########################################
class FlowNode(BaseModel):
    id: str
    type: str
    data: Dict[str, Any]
    position: Dict[str, float]

class FlowEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str]

class FlowDiagram(BaseModel):
    id: str
    title: str
    owner: Optional[str]
    nodes: List[FlowNode]
    edges: List[FlowEdge]
    created_at: Optional[str]
    updated_at: Optional[str]

class CreateFlowRequest(BaseModel):
    title: str
    nodes: List[FlowNode]
    edges: List[FlowEdge]

class UpdateFlowRequest(BaseModel):
    title: Optional[str]
    nodes: Optional[List[FlowNode]]
    edges: Optional[List[FlowEdge]]

class RunCodeRequest(BaseModel):
    flow_id: str = Field(..., description="ID of the flow to execute")
    inputs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Input values for execution")

class RunCodeResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    execution_id: str

class ExecutionResultHistory(BaseModel):
    id: str
    flow_id: str
    user: Optional[str] = None
    timestamp: str
    result: RunCodeResult

#########################################
# --- In-Memory Placeholders ---
#########################################
# Replace with actual DB integration
FLOWS = {}
RESULTS = {}

#########################################
# --- Basic Health Check ---
#########################################

@app.get("/", summary="Health Check", tags=["health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "Healthy"}

#########################################
# --- Flow CRUD Endpoints ---
#########################################

# PUBLIC_INTERFACE
@app.get("/flows", response_model=List[FlowDiagram], summary="List all flows", tags=["flows"])
def list_flows():
    """
    List all flows.
    """
    return list(FLOWS.values())

# PUBLIC_INTERFACE
@app.post("/flows", response_model=FlowDiagram, summary="Create a new flow", tags=["flows"])
def create_flow(request: CreateFlowRequest):
    """
    Create a new flow.
    """
    flow_id = str(uuid.uuid4())
    new_flow = FlowDiagram(
        id=flow_id,
        title=request.title,
        owner=None,
        nodes=request.nodes,
        edges=request.edges,
        created_at="",  # placeholder
        updated_at=""
    )
    FLOWS[flow_id] = new_flow
    return new_flow

# PUBLIC_INTERFACE
@app.get("/flows/{flow_id}", response_model=FlowDiagram, summary="Get a specific flow", tags=["flows"])
def get_flow(flow_id: str):
    """
    Get a specific flow diagram by ID.
    """
    flow = FLOWS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow

# PUBLIC_INTERFACE
@app.put("/flows/{flow_id}", response_model=FlowDiagram, summary="Update a flow", tags=["flows"])
def update_flow(flow_id: str, request: UpdateFlowRequest):
    """
    Update a flow (title, structure).
    """
    flow = FLOWS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    if request.title is not None:
        flow.title = request.title
    if request.nodes is not None:
        flow.nodes = request.nodes
    if request.edges is not None:
        flow.edges = request.edges
    # Update timestamp fields, etc.
    return flow

# PUBLIC_INTERFACE
@app.delete("/flows/{flow_id}", summary="Delete a flow", tags=["flows"])
def delete_flow(flow_id: str):
    """
    Delete a flow by ID.
    """
    flow = FLOWS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    del FLOWS[flow_id]
    return {"message": "Flow deleted"}

#########################################
# --- JavaScript Execution Endpoint ---
#########################################

# PUBLIC_INTERFACE
@app.post("/execute", response_model=RunCodeResult, summary="Execute JavaScript for a flow", tags=["execution"])
def execute_js_flow(request: RunCodeRequest):
    """
    Executes the JavaScript code associated with the flow.
    Uses a subprocess call to Node.js for sandboxed execution.
    NOTE: Real implementation MUST sandbox/validate code securely!
    """
    flow = FLOWS.get(request.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    # For now, let's assume that the "nodes" contain a code block under "data" key.
    # We'll concatenate any code blocks for demo.
    js_code_segments = [
        node.data.get("code") for node in flow.nodes if "code" in node.data
    ]
    full_code = "\n".join(js_code_segments)
    execution_id = str(uuid.uuid4())

    try:
        # This is a simple, non-secure runner for demonstration!
        # In production: use dockerized sandbox, VM, or nodejs process with time/memory limits!
        result = subprocess.run(
            ["node", "-e", full_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            error = None
            success = True
        else:
            output = result.stdout.strip()
            error = result.stderr.strip()
            success = False
    except Exception as e:
        output = ""
        error = str(e)
        success = False

    run_result = RunCodeResult(
        success=success,
        output=output,
        error=error,
        execution_id=execution_id,
    )
    RESULTS[execution_id] = {
        "result": run_result,
        "user": None,
        "flow_id": request.flow_id,
        "timestamp": "",  # set timestamp here
    }
    return run_result

#########################################
# --- Result Management Endpoints ---
#########################################

# PUBLIC_INTERFACE
@app.get("/results", response_model=List[ExecutionResultHistory], summary="Get all execution results", tags=["results"])
def get_all_results():
    """
    Get all execution results.
    """
    return [
        ExecutionResultHistory(
            id=k,
            flow_id=v["flow_id"],
            user=None,
            timestamp=v.get("timestamp", ""),
            result=v["result"]
        )
        for k, v in RESULTS.items()
    ]

# PUBLIC_INTERFACE
@app.get("/results/{execution_id}", response_model=ExecutionResultHistory, summary="Get result by execution ID", tags=["results"])
def get_result(execution_id: str):
    """
    Get a specific execution result by result ID.
    """
    result_data = RESULTS.get(execution_id)
    if not result_data:
        raise HTTPException(status_code=404, detail="Result not found")
    return ExecutionResultHistory(
        id=execution_id,
        flow_id=result_data["flow_id"],
        user=None,
        timestamp=result_data.get("timestamp", ""),
        result=result_data["result"]
    )

#########################################
# --- Swagger/WebSocket Usage Help ---
#########################################

@app.get("/docs/ws-help", tags=["execution"], summary="WebSocket Usage Help")
def ws_usage_help():
    """
    WebSocket is not implemented in this backend. All JS execution is synchronous via REST API.
    """
    return {
        "info": "This backend exposes HTTP REST endpoints for all operations. Real-time WebSocket communication is not implemented in this version."
    }
