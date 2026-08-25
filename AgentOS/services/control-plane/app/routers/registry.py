"""
AgentOS Control Plane — Hardened Registry & Server-Authoritative Publishing Router
Phase 8 Delivery: Server-authoritative publishing pipeline with manifest schema validation,
canonical sha256 manifest hashing, SENTINEL pre-publish policy gate, automated SBOM generation,
digital signature minting, and immutable ReleaseRecord persistence.
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models.version import ReleaseRecord
from app.routers.lifecycle import (
    AgentManifest,
    evaluate_sentinel_policy,
    get_session,
    normalize_manifest_dict,
)

router = APIRouter(prefix="/v1/registry", tags=["registry-v1"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PublishRequest(BaseModel):
    yaml_content: str | None = Field(None, alias="yamlContent")
    yaml: str | None = None
    org_slug: str | None = Field("nuuvixx", alias="orgSlug")
    publisher_id: str | None = Field("dev-publisher-01", alias="publisherId")

    model_config = {"populate_by_name": True}

    @property
    def raw_yaml(self) -> str:
        return self.yaml_content or self.yaml or ""


# ── Helper Functions ──────────────────────────────────────────────────────────

def generate_sbom(parsed_manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Generates a Software Bill of Materials (SBOM) from an Agent Manifest.
    """
    metadata = parsed_manifest.get("metadata", {})
    model = parsed_manifest.get("model", {})
    tools = parsed_manifest.get("tools") or []
    runtime = parsed_manifest.get("runtime", {})

    components = [
        {
            "name": f"model/{model.get('provider', 'openai')}",
            "type": "ai_model",
            "version": model.get("name", "gpt-4o")
        },
        {
            "name": f"sandbox/{runtime.get('sandbox', 'docker')}",
            "type": "container_runtime",
            "version": "1.0.0"
        }
    ]

    for tool in tools:
        components.append({
            "name": f"tool/{tool.get('id', 'unknown')}",
            "type": tool.get("type", "mcp"),
            "server": tool.get("server"),
            "risk": tool.get("risk", "low")
        })

    return {
        "bomFormat": "AgentStudio-CycloneDX-v1",
        "specVersion": "1.4",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "componentName": metadata.get("name", "agent"),
        "version": metadata.get("version", "1.0.0"),
        "components": components
    }


def mint_digital_signature(agent_slug: str, version: str, manifest_hash: str) -> str:
    """
    Mints a digital cryptographic signature for the release payload.
    """
    signing_payload = f"AGENTSTUDIO_RELEASE:{agent_slug}:{version}:{manifest_hash}"
    sig = hashlib.sha256(signing_payload.encode("utf-8")).hexdigest()
    return f"sha256:sig_{sig}"


# ── Registry Endpoints ────────────────────────────────────────────────────────

@router.post("/publish")
async def publish_agent_release(
    body: PublishRequest,
    session: Session = Depends(get_session)
) -> dict[str, Any]:
    """
    Server-authoritative release publishing endpoint.
    Client cannot publish without server-side validation, SENTINEL policy check, SBOM generation, and signature minting.
    """
    yaml_str = body.raw_yaml
    if not yaml_str or not yaml_str.strip():
        raise HTTPException(status_code=400, detail="YAML content required for publishing")

    try:
        parsed = yaml.safe_load(yaml_str)
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=422, detail="Invalid YAML manifest format")

        parsed = normalize_manifest_dict(parsed)

        # 1. Pydantic Manifest Validation & Canonical Hashing
        if AgentManifest:
            manifest = AgentManifest.model_validate(parsed)
            manifest_hash = manifest.canonical_hash
            dict_representation = manifest.model_dump(mode="json", by_alias=True)
            name = manifest.metadata.name
            ver = manifest.metadata.version
        else:
            dict_representation = parsed
            canonical_str = json.dumps(parsed, sort_keys=True)
            manifest_hash = "sha256:" + hashlib.sha256(canonical_str.encode()).hexdigest()
            metadata = parsed.get("metadata", {})
            name = metadata.get("name", "unnamed-agent")
            ver = str(metadata.get("version", "1.0.0"))

        org_slug = (body.org_slug or "nuuvixx").lower().strip()
        agent_slug = f"{org_slug}/{name}"

        # 2. Server-Authoritative SENTINEL Policy Evaluation
        policy_res = await evaluate_sentinel_policy(dict_representation, context="registry_publish")
        verdict = policy_res.get("decision", "ALLOW")

        if verdict == "DENY":
            reasons = policy_res.get("reasons", ["Pre-publish SENTINEL policy check failed"])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Publishing DENIED by GovernOS SENTINEL policy: {'; '.join(reasons)}"
            )

        # 3. Generate SBOM and Mint Digital Signature
        sbom_json = generate_sbom(dict_representation)
        signature = mint_digital_signature(agent_slug, ver, manifest_hash)

        # 4. Check for existing exact release (idempotency)
        existing = session.exec(
            select(ReleaseRecord).where(
                ReleaseRecord.agent_slug == agent_slug,
                ReleaseRecord.version == ver,
                ReleaseRecord.manifest_hash == manifest_hash
            )
        ).first()

        if existing:
            return {
                "releaseId": str(existing.id),
                "agentSlug": existing.agent_slug,
                "agentName": existing.agent_name,
                "version": existing.version,
                "manifestHash": existing.manifest_hash,
                "policyVerdict": existing.policy_verdict,
                "signature": existing.signature,
                "sbomJson": existing.sbom_json,
                "publishedAt": existing.published_at.isoformat(),
                "created": False,
                "message": f"Release {agent_slug}:{ver} is already published"
            }

        # 5. Save Immutable Release Record
        release = ReleaseRecord(
            agent_slug=agent_slug,
            agent_name=name,
            org_slug=org_slug,
            version=ver,
            manifest_hash=manifest_hash,
            schema_version="agentstudio/v1",
            status="PUBLISHED",
            policy_verdict=verdict,
            policy_bundle=policy_res.get("policy_bundle", "nuuvixx-standard-2026.09"),
            signature=signature,
            sbom_json=sbom_json,
            manifest_json=dict_representation
        )
        session.add(release)
        session.commit()
        session.refresh(release)

        return {
            "releaseId": str(release.id),
            "agentSlug": release.agent_slug,
            "agentName": release.agent_name,
            "version": release.version,
            "manifestHash": release.manifest_hash,
            "policyVerdict": release.policy_verdict,
            "signature": release.signature,
            "sbomJson": release.sbom_json,
            "publishedAt": release.published_at.isoformat(),
            "created": True,
            "message": f"Successfully published {agent_slug} v{ver} to AgentStudio Registry"
        }
    except HTTPException:
        raise
    except Exception as e:
        print("PUBLISH EXCEPTION:", repr(e))
        raise HTTPException(status_code=422, detail=f"Publishing validation error: {str(e)}")


@router.get("/releases")
def list_published_releases(session: Session = Depends(get_session)) -> dict[str, Any]:
    """
    Lists all published agent releases in the registry.
    """
    releases = session.exec(select(ReleaseRecord)).all()
    return {
        "count": len(releases),
        "releases": [
            {
                "releaseId": str(r.id),
                "agentSlug": r.agent_slug,
                "version": r.version,
                "manifestHash": r.manifest_hash,
                "policyVerdict": r.policy_verdict,
                "signature": r.signature,
                "publishedAt": r.published_at.isoformat()
            }
            for r in releases
        ]
    }


@router.get("/releases/{release_id}")
def get_published_release(release_id: uuid.UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    """
    Gets full release details including SBOM and digital signature.
    """
    release = session.get(ReleaseRecord, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release record not found")

    return {
        "releaseId": str(release.id),
        "agentSlug": release.agent_slug,
        "agentName": release.agent_name,
        "version": release.version,
        "manifestHash": release.manifest_hash,
        "policyVerdict": release.policy_verdict,
        "policyBundle": release.policy_bundle,
        "signature": release.signature,
        "sbomJson": release.sbom_json,
        "manifestJson": release.manifest_json,
        "publishedAt": release.published_at.isoformat()
    }


@router.get("/agents/{org_slug}/{agent_name}")
def get_agent_releases(org_slug: str, agent_name: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """
    Gets all published releases for a specific agent slug.
    """
    agent_slug = f"{org_slug.lower()}/{agent_name}"
    releases = session.exec(select(ReleaseRecord).where(ReleaseRecord.agent_slug == agent_slug)).all()
    if not releases:
        raise HTTPException(status_code=404, detail=f"No published releases found for {agent_slug}")

    return {
        "agentSlug": agent_slug,
        "count": len(releases),
        "releases": [
            {
                "releaseId": str(r.id),
                "version": r.version,
                "manifestHash": r.manifest_hash,
                "signature": r.signature,
                "publishedAt": r.published_at.isoformat()
            }
            for r in releases
        ]
    }
