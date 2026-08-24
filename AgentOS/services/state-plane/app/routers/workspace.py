from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter(prefix="/workspace", tags=["workspace"])

# Simple local filesystem mock for Phase 1. 
# Phase 2 will use S3 or distributed shared volume.
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/tmp/agentos_workspaces")
os.makedirs(WORKSPACE_ROOT, exist_ok=True)

class FileWriteRequest(BaseModel):
    content: str

@router.post("/{agent_id}/files/{file_path:path}")
def write_file(agent_id: str, file_path: str, req: FileWriteRequest):
    agent_dir = os.path.join(WORKSPACE_ROOT, agent_id)
    os.makedirs(agent_dir, exist_ok=True)
    
    target_path = os.path.join(agent_dir, file_path)
    # Ensure it's safe and inside agent_dir
    if not os.path.abspath(target_path).startswith(os.path.abspath(agent_dir)):
        raise HTTPException(status_code=403, detail="Invalid path")
        
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(req.content)
    return {"status": "written", "path": file_path}

@router.get("/{agent_id}/files/{file_path:path}")
def read_file(agent_id: str, file_path: str):
    target_path = os.path.join(WORKSPACE_ROOT, agent_id, file_path)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content}
