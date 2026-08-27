"""
Policy Versioning Service

Handles saving versions of policies on update, generating diffs,
and rolling back to previous versions.
"""

import uuid
from collections.abc import Sequence
from copy import deepcopy
from typing import Any

from models import Policy, PolicyVersion
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


class PolicyVersioner:
    
    @staticmethod
    def generate_diff(old_content: dict[str, Any], new_content: dict[str, Any]) -> dict[str, Any]:
        """
        Generates a simplified JSON diff between two dictionaries.
        """
        diff = {"added": {}, "removed": {}, "changed": {}}
        
        # Simple diff implementation for demo purposes
        for k, v in new_content.items():
            if k not in old_content:
                diff["added"][k] = v
            elif old_content[k] != v:
                diff["changed"][k] = {"old": old_content[k], "new": v}
                
        for k, v in old_content.items():
            if k not in new_content:
                diff["removed"][k] = v
                
        return diff

    async def save_version(self, db: AsyncSession, policy: Policy, updated_by: str = "system") -> PolicyVersion:
        """
        Takes the current state of a policy and saves it as a new version.
        Call this BEFORE committing the changes to the Policy model if you want
        to track the PREVIOUS state, or call it AFTER if you want to track the NEW state.
        We'll track the state at the time of calling.
        """
        content = {
            "policy_name": policy.policy_name,
            "category": policy.category,
            "description": policy.description,
            "rule_definition": deepcopy(policy.rule_definition),
            "applies_to_roles": deepcopy(policy.applies_to_roles),
            "applies_to_tiers": deepcopy(policy.applies_to_tiers),
            "severity": policy.severity,
            "action_on_violation": policy.action_on_violation,
            "is_active": policy.is_active
        }
        
        # Find latest version to calculate diff
        latest_res = await db.execute(
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy.id)
            .order_by(desc(PolicyVersion.version))
            .limit(1)
        )
        latest_version = latest_res.scalar_one_or_none()
        
        diff = None
        if latest_version:
            diff = self.generate_diff(latest_version.content_json, content)
            
        new_version_num = policy.version
        
        pv = PolicyVersion(
            policy_id=policy.id,
            version=new_version_num,
            content_json=content,
            diff=diff,
            created_by=updated_by
        )
        
        db.add(pv)
        await db.commit()
        await db.refresh(pv)
        
        return pv

    async def get_history(self, db: AsyncSession, policy_id: uuid.UUID) -> Sequence[PolicyVersion]:
        """
        Retrieves the version history of a policy.
        """
        result = await db.execute(
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id)
            .order_by(desc(PolicyVersion.version))
        )
        return result.scalars().all()
        
    async def rollback(self, db: AsyncSession, policy_id: uuid.UUID, target_version: int, updated_by: str = "system") -> Policy:
        """
        Rolls a policy back to a previous version, incrementing the version number overall.
        """
        # Get target version
        target_res = await db.execute(
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id, PolicyVersion.version == target_version)
        )
        target = target_res.scalar_one_or_none()
        if not target:
            raise ValueError(f"Version {target_version} not found for policy.")
            
        # Get current policy
        policy = await db.get(Policy, policy_id)
        if not policy:
            raise ValueError("Policy not found.")
            
        # Apply content
        content = target.content_json
        policy.policy_name = content.get("policy_name", policy.policy_name)
        policy.category = content.get("category", policy.category)
        policy.description = content.get("description", policy.description)
        policy.rule_definition = content.get("rule_definition", policy.rule_definition)
        policy.applies_to_roles = content.get("applies_to_roles", policy.applies_to_roles)
        policy.applies_to_tiers = content.get("applies_to_tiers", policy.applies_to_tiers)
        policy.severity = content.get("severity", policy.severity)
        policy.action_on_violation = content.get("action_on_violation", policy.action_on_violation)
        policy.is_active = content.get("is_active", policy.is_active)
        
        # Increment version
        policy.version += 1
        
        # Save new version record
        await self.save_version(db, policy, updated_by=updated_by)
        
        return policy
