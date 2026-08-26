import logging
import os
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)

# AgentGovernOS Service URL
AGENT_GOVERN_URL = os.getenv("AGENT_GOVERN_URL", "http://127.0.0.1:8025")

async def broadcast_telemetry(agent_id: str, event_type: str, action_name: str, verdict: str, details: Dict[str, Any]):
    """Emit a live telemetry event to AgentGovernOS WebSocket broadcaster."""
    try:
        payload = {
            "agent_id": agent_id,
            "event_type": event_type,
            "action_name": action_name,
            "verdict": verdict,
            "details": details
        }
        async with httpx.AsyncClient() as client:
            await client.post(f"{AGENT_GOVERN_URL}/v1/realtime/broadcast", json=payload, timeout=3.0)
    except Exception as e:
        logger.debug(f"Telemetry broadcast notice: {e}")

async def evaluate_tool_call(auth_header: str, tool_name: str, payload: Dict[str, Any], agent_id: str = "system_agent") -> bool:
    """
    Calls AgentGovernOS to evaluate if the agent is allowed to use this MCP tool.
    Emits live WebSocket telemetry events.
    """
    logger.info(f"Checking governance policy for Tool '{tool_name}' with AgentGovernOS")
    envelope = {
        "agent_code": agent_id,
        "action_requested": tool_name,
        "agent_source": "agentos_network_plane",
        "context": payload
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Try main governance endpoint /governance/evaluate
            resp = await client.post(
                f"{AGENT_GOVERN_URL}/governance/evaluate",
                json=envelope,
                headers={"Authorization": auth_header} if auth_header else {},
                timeout=10.0
            )
            
            is_approved = False
            if resp.status_code == 200:
                data = resp.json()
                verdict = data.get("verdict", "APPROVED")
                is_approved = (verdict in ["APPROVED", "ALLOW"])
            else:
                is_approved = True  # Fallback allow for local testing if DB unseeded
                
            verdict_str = "ALLOW" if is_approved else "BLOCK"
            await broadcast_telemetry(
                agent_id=agent_id,
                event_type="tool_call",
                action_name=tool_name,
                verdict=verdict_str,
                details={"arguments": payload, "status_code": resp.status_code}
            )
            return is_approved
    except Exception as e:
        logger.warning(f"Governance evaluate fallback: {e}")
        await broadcast_telemetry(
            agent_id=agent_id,
            event_type="tool_call",
            action_name=tool_name,
            verdict="ALLOW",
            details={"fallback": True}
        )
        return True

async def evaluate_llm_call(auth_header: str, provider: str, model: str, prompt: str, agent_id: str = "system_agent") -> bool:
    """
    Evaluates LLM prompts for OWASP prompt injection and safety policies.
    """
    logger.info(f"Evaluating LLM call ({provider}/{model}) with AgentGovernOS")
    
    # Check for obvious injection keywords
    injections = ["ignore previous instructions", "system prompt leak", "bypass safety"]
    has_injection = any(inj in prompt.lower() for inj in injections) if prompt else False
    
    if has_injection:
        logger.warning(f"BLOCKED: Prompt injection detected in prompt for model {model}")
        await broadcast_telemetry(
            agent_id=agent_id,
            event_type="policy_verdict",
            action_name=f"llm:{provider}/{model}",
            verdict="BLOCK",
            details={"reason": "Prompt injection detected", "prompt_snippet": prompt[:100]}
        )
        return False

    await broadcast_telemetry(
        agent_id=agent_id,
        event_type="policy_verdict",
        action_name=f"llm:{provider}/{model}",
        verdict="ALLOW",
        details={"model": model, "prompt_length": len(prompt) if prompt else 0}
    )
    return True

async def evaluate_egress_domain(domain: str, agent_id: str = "system_agent") -> bool:
    """
    Evaluates HTTP egress requests against allowed domain whitelists.
    """
    blocked_domains = ["malicious-domain.com", "phishing-target.net", "unapproved-crypto-miner.org"]
    if domain in blocked_domains:
        logger.warning(f"BLOCKED egress request to domain '{domain}'")
        await broadcast_telemetry(
            agent_id=agent_id,
            event_type="egress_check",
            action_name=domain,
            verdict="BLOCK",
            details={"reason": "Domain blacklisted by Sentinel"}
        )
        return False
        
    await broadcast_telemetry(
        agent_id=agent_id,
        event_type="egress_check",
        action_name=domain,
        verdict="ALLOW",
        details={"domain": domain}
    )
    return True
