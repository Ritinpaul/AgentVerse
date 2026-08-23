"""
app/sandbox/policy_interceptor.py

Server-authoritative runtime policy enforcement interceptor.
Enforces:
1. Tool Risk Policy (blocking critical/high-risk tools if required by policy)
2. Network Egress Restrictions (domain whitelisting against permissions.egress)
3. Cumulative Budget Counter (terminating runs when maxCostPerRun ceiling is exceeded)
"""

from typing import Dict, Any


class ToolPolicyViolationError(Exception):
    pass


class EgressViolationError(Exception):
    pass


class BudgetExceededError(Exception):
    pass


class RuntimePolicyInterceptor:
    """
    Evaluates every tool call before execution against manifest policy bundle.
    """

    @staticmethod
    def validate_tool_call(
        tool: Dict[str, Any],
        inputs: Dict[str, Any],
        policy_cfg: Dict[str, Any],
        runtime_cfg: Dict[str, Any],
        budget_cfg: Dict[str, Any],
        current_cumulative_cost: float,
        step_estimated_cost: float = 0.01
    ) -> None:
        # 1. Budget Counter Check
        max_cost = budget_cfg.get("maxCostPerRun") or budget_cfg.get("max_cost_per_run") or 10.0
        if current_cumulative_cost + step_estimated_cost > max_cost:
            raise BudgetExceededError(
                f"Cumulative cost (${current_cumulative_cost + step_estimated_cost:.4f}) exceeds max allowed budget (${max_cost:.2f})"
            )

        # 2. Tool Risk Check
        risk = (tool.get("risk") or "low").lower()
        approval = policy_cfg.get("approval", {})
        if not isinstance(approval, dict):
            approval = {}

        critical_policy = approval.get("criticalRiskToolCalls", "block")
        high_risk_policy = approval.get("highRiskToolCalls", "required")

        if risk == "critical" and critical_policy == "block":
            raise ToolPolicyViolationError(
                f"Tool '{tool.get('id')}' has CRITICAL risk and criticalRiskToolCalls is set to 'block'"
            )

        if risk == "high" and high_risk_policy == "block":
            raise ToolPolicyViolationError(
                f"Tool '{tool.get('id')}' has HIGH risk and highRiskToolCalls is set to 'block'"
            )

        # 3. Network Egress Domain Whitelist Check
        egress_mode = (runtime_cfg.get("egress") or "restricted").lower()
        if egress_mode == "none":
            if tool.get("type") in ["http", "mcp"] or "url" in inputs:
                raise EgressViolationError(
                    f"Tool '{tool.get('id')}' attempted network access, but runtime egress is set to 'none'"
                )

        if egress_mode == "restricted":
            target_url = inputs.get("url") or tool.get("url") or ""
            if target_url:
                from urllib.parse import urlparse
                hostname = urlparse(target_url).hostname or target_url
                tool_permissions = tool.get("permissions") or {}
                allowed_domains = tool_permissions.get("egress") or []

                if allowed_domains and not any(
                    hostname == domain or hostname.endswith("." + domain) for domain in allowed_domains
                ):
                    raise EgressViolationError(
                        f"Domain '{hostname}' is not in allowed egress whitelist {allowed_domains}"
                    )
