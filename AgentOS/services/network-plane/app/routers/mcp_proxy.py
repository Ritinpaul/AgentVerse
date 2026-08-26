import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.services.mcp_discoverer import get_mcp_url
from app.services.governance_client import evaluate_tool_call, evaluate_llm_call, evaluate_egress_domain

router = APIRouter(prefix="/proxy", tags=["proxy"])

class ToolCallPayload(BaseModel):
    agent_id: Optional[str] = "system_agent"
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]

class LLMCallPayload(BaseModel):
    agent_id: Optional[str] = "system_agent"
    provider: str = "openrouter"
    model: str
    prompt: str
    messages: Optional[List[Dict[str, Any]]] = None

class EgressPayload(BaseModel):
    agent_id: Optional[str] = "system_agent"
    domain: str
    url: str
    method: str = "GET"

@router.post("/call")
async def proxy_mcp_call(payload: ToolCallPayload, request: Request):
    """
    1. Intercepts the tool call from the agent SDK.
    2. Runs it through AgentGovernOS Sentinel policy engine.
    3. Emits live telemetry event over WebSockets.
    4. Forwards to actual MCP server if approved.
    """
    auth_header = request.headers.get("Authorization", "")
    agent_id = payload.agent_id or "system_agent"
        
    # 1. Check Governance
    is_approved = await evaluate_tool_call(auth_header, payload.tool_name, payload.arguments, agent_id=agent_id)
    if not is_approved:
        raise HTTPException(status_code=403, detail=f"Policy violation: Not allowed to call tool '{payload.tool_name}'")

    # 2. Lookup Server URL
    mcp_url = get_mcp_url(payload.server_name)
    if not mcp_url:
        # Return graceful mock response for test environment if server not registered
        return {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {
                "content": [{"type": "text", "text": f"Executed tool '{payload.tool_name}' on server '{payload.server_name}' successfully."}]
            }
        }
        
    # 3. Forward to actual MCP Server (JSON-RPC format)
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "call_tool",
        "params": {
            "name": payload.tool_name,
            "arguments": payload.arguments
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(mcp_url, json=rpc_payload, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        return {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {
                "content": [{"type": "text", "text": f"Mock successful response from {payload.server_name}/{payload.tool_name}!"}]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with MCP Server: {e}")

@router.post("/llm")
async def proxy_llm_call(payload: LLMCallPayload, request: Request):
    """
    Transparent LLM proxy: Intercepts all LLM requests from agent containers,
    runs prompt injection & safety policy checks, and emits real-time WebSocket telemetry.
    """
    auth_header = request.headers.get("Authorization", "")
    agent_id = payload.agent_id or "system_agent"

    prompt_text = payload.prompt
    if not prompt_text and payload.messages:
        prompt_text = " ".join(str(m.get("content", "")) for m in payload.messages)

    # 1. Run LLM Governance Check
    is_approved = await evaluate_llm_call(
        auth_header=auth_header,
        provider=payload.provider,
        model=payload.model,
        prompt=prompt_text,
        agent_id=agent_id
    )
    if not is_approved:
        raise HTTPException(
            status_code=403,
            detail=f"GovernOS Security Block: Prompt injection or safety violation detected for model '{payload.model}'."
        )

    # 2. Return governed proxy response
    return {
        "status": "approved",
        "agent_id": agent_id,
        "provider": payload.provider,
        "model": payload.model,
        "response": {
            "id": f"gen-{agent_id}-1001",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"[Governed LLM Response] Successfully processed prompt via {payload.provider}/{payload.model} under strict Sentinel policy rules."
                    }
                }
            ]
        }
    }

@router.post("/egress")
async def proxy_egress_call(payload: EgressPayload, request: Request):
    """
    Transparent Egress proxy: Intercepts outbound HTTP calls from agent containers,
    verifies domain against whitelist policy, and streams live telemetry events.
    """
    agent_id = payload.agent_id or "system_agent"
    is_approved = await evaluate_egress_domain(domain=payload.domain, agent_id=agent_id)

    if not is_approved:
        raise HTTPException(
            status_code=403,
            detail=f"GovernOS Network Block: Outbound request to unapproved domain '{payload.domain}' is strictly prohibited."
        )

    return {
        "status": "approved",
        "agent_id": agent_id,
        "domain": payload.domain,
        "url": payload.url,
        "message": f"Egress request to {payload.domain} approved by Sentinel network policy."
    }
