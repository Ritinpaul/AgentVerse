from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from app.db.session import get_db
from app.models.agent_listing import AgentListing, AgentVersion
from app.services.yaml_validator import validate_agent_yaml
from app.services.slug_generator import generate_agent_slug
from app.services.search_engine import index_agent_to_elasticsearch
from app.core.rate_limit import mutation_limit

router = APIRouter(prefix="/registry/agents", tags=["Registry - Agents"])

MAX_YAML_BYTES = 64_000  # 64 KB cap

from app.core.auth_middleware import get_current_user, UserIdentity

def check_agent_ownership(listing: AgentListing, user: UserIdentity):
    """Enforces RBAC: User can only modify agents they built, unless admin/service account."""
    if user.is_service or user.role in ["admin", "owner"]:
        return
    if listing.builder_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ownership violation: Organization '{user.org_id}' cannot modify agent owned by '{listing.builder_id}'"
        )

def _validate_payload_size(raw_yaml: Optional[str]):
    if raw_yaml and len(raw_yaml.encode("utf-8")) > MAX_YAML_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": f"agent_yaml exceeds {MAX_YAML_BYTES // 1000} KB size limit"}
        )

# Request/Response Schemas
class PublishAgentRequest(BaseModel):
    builder_id: Optional[str] = Field(None, description="Builder or Organization ID")
    agent_yaml: Optional[str] = Field(None, description="Raw YAML manifest content")
    category: str = Field("general", description="Category e.g. support, security, devops, finance")
    # Extended fields for direct JSON payload publishing
    apiVersion: Optional[str] = None
    kind: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    spec: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None

class PublishVersionRequest(BaseModel):
    agent_yaml: str = Field(..., description="Raw YAML manifest content for new version")
    changelog: str = Field("", description="Release notes or changelog")

class AgentVersionResponse(BaseModel):
    id: int
    version_semver: str
    agent_yaml: str
    changelog: Optional[str] = None
    status: str
    published_at: str

    model_config = ConfigDict(from_attributes=True)

class AgentListingResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    builder_id: str
    category: str
    tags: List[str] = []
    capabilities: List[str] = []
    current_version: str
    status: str
    trust_score: float
    created_at: str
    runtime: Optional[Dict[str, Any]] = None
    price_per_execution: Optional[float] = 0.05
    total_executions: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

class AgentDetailResponse(AgentListingResponse):
    versions: List[AgentVersionResponse] = []


@router.post("", response_model=AgentListingResponse, status_code=status.HTTP_201_CREATED)
@mutation_limit("5/minute")
def publish_agent(
    request: Request,
    payload: PublishAgentRequest,
    db: Session = Depends(get_db),
    current_user: UserIdentity = Depends(get_current_user)
):
    import yaml as pyyaml
    
    _validate_payload_size(payload.agent_yaml)
    
    # Auto-assign builder_id from user's org unless admin/service account overrides
    if current_user.is_service or current_user.role in ["admin", "owner"]:
        builder_id = payload.builder_id or current_user.org_id
    else:
        builder_id = current_user.org_id

    # Handle structured JSON payload
    if not payload.agent_yaml and payload.metadata:
        manifest_dict = payload.model_dump(exclude_none=True)
        raw_yaml = pyyaml.dump(manifest_dict)
    else:
        raw_yaml = payload.agent_yaml or ""

    is_valid, errors, data = validate_agent_yaml(raw_yaml)
    if not is_valid or not data:
        # Fallback for dynamic manifests
        data = payload.metadata or {}
        if not data.get("name"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": "Invalid agent manifest", "errors": errors})

    name = data.get("name", "untitled-agent")
    version = data.get("version", "0.1.0")
    description = data.get("description", "No description provided.")
    tools_list = data.get("tools", [])
    
    tags = [data.get("framework", "custom")]
    capabilities = [f"tool:{t.get('tool')}" for t in tools_list if isinstance(t, dict) and "tool" in t]
    
    slug = generate_agent_slug(builder_id, name, db)
    
    listing = AgentListing(
        slug=slug,
        name=name,
        description=description,
        builder_id=builder_id,
        category=payload.category.lower(),
        tags=list(set(tags)),
        capabilities=capabilities,
        current_version=version,
        status="active",
        trust_score=0.0
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    
    ver = AgentVersion(
        listing_id=listing.id,
        version_semver=version,
        agent_yaml=payload.agent_yaml or raw_yaml,
        changelog="Initial publication.",
        status="published"
    )
    db.add(ver)
    db.commit()
    
    index_agent_to_elasticsearch(listing)
    
    return _format_listing_response(listing)


@router.post("/{slug:path}/versions", response_model=AgentVersionResponse, status_code=status.HTTP_201_CREATED)
@mutation_limit("10/minute")
def publish_version(
    request: Request,
    slug: str,
    payload: PublishVersionRequest,
    db: Session = Depends(get_db),
    current_user: UserIdentity = Depends(get_current_user)
):
    _validate_payload_size(payload.agent_yaml)
    
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent listing not found.")
        
    check_agent_ownership(listing, current_user)

    is_valid, errors, data = validate_agent_yaml(payload.agent_yaml)
    if not is_valid or not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": "Invalid agent.yaml manifest", "errors": errors})
        
    version = data.get("version", "0.1.0")
    existing_ver = db.query(AgentVersion).filter(AgentVersion.listing_id == listing.id, AgentVersion.version_semver == version).first()
    if existing_ver:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Version {version} already published for this agent.")
        
    ver = AgentVersion(
        listing_id=listing.id,
        version_semver=version,
        agent_yaml=payload.agent_yaml,
        changelog=payload.changelog,
        status="published"
    )
    listing.current_version = version
    listing.description = data.get("description", listing.description)
    
    db.add(ver)
    db.commit()
    db.refresh(ver)
    
    index_agent_to_elasticsearch(listing)
    
    return _format_ver_response(ver)


@router.get("", response_model=List[AgentListingResponse])
def list_agents(
    category: Optional[str] = None,
    skip: int = Query(0, ge=0, le=10000),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    query = db.query(AgentListing).options(joinedload(AgentListing.versions)).filter(AgentListing.status == "active")
    if category and category.lower() != "all":
        query = query.filter(AgentListing.category == category.lower())
    listings = query.order_by(AgentListing.trust_score.desc()).offset(skip).limit(limit).all()
    return [_format_listing_response(l) for l in listings]


@router.get("/{slug:path}/versions", response_model=List[AgentVersionResponse])
def get_agent_versions(slug: str, db: Session = Depends(get_db)):
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent listing not found.")
    return [_format_ver_response(v) for v in listing.versions]


@router.delete("/{slug:path}/versions/{version}", status_code=status.HTTP_200_OK)
def retract_version(
    slug: str,
    version: str,
    db: Session = Depends(get_db),
    current_user: UserIdentity = Depends(get_current_user)
):
    listing = db.query(AgentListing).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent listing not found.")
    
    check_agent_ownership(listing, current_user)
    
    ver = db.query(AgentVersion).filter(AgentVersion.listing_id == listing.id, AgentVersion.version_semver == version).first()
    if not ver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
        
    ver.status = "retracted"
    db.commit()
    return {"message": f"Version {version} of {slug} has been retracted."}


@router.get("/{slug:path}", response_model=AgentDetailResponse)
def get_agent_detail(slug: str, db: Session = Depends(get_db)):
    listing = db.query(AgentListing).options(joinedload(AgentListing.versions)).filter(AgentListing.slug == slug).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent listing not found.")
    
    res = _format_listing_response(listing).model_dump()
    res["versions"] = [_format_ver_response(v) for v in listing.versions]
    return res


def _format_listing_response(l: AgentListing) -> AgentListingResponse:
    model_name = "gemini-1.5-flash"
    fallback_model = "gpt-4o-mini"
    max_tokens = 4096
    timeout_seconds = 30
    
    if l.versions:
        try:
            import yaml as pyyaml
            ver = next((v for v in l.versions if v.version_semver == l.current_version), l.versions[-1])
            if ver and ver.agent_yaml:
                parsed = pyyaml.safe_load(ver.agent_yaml)
                if isinstance(parsed, dict):
                    m = parsed.get("model")
                    if isinstance(m, dict) and m.get("name"):
                        model_name = m.get("name")
                    elif isinstance(m, str) and m:
                        model_name = m
                    elif parsed.get("runtime", {}).get("model"):
                        model_name = parsed["runtime"]["model"]
        except Exception:
            pass

    return AgentListingResponse(
        id=l.id,
        slug=l.slug,
        name=l.name,
        description=l.description,
        builder_id=l.builder_id,
        category=l.category,
        tags=l.tags or [],
        capabilities=l.capabilities or [],
        current_version=l.current_version,
        status=l.status,
        trust_score=l.trust_score,
        created_at=l.created_at.isoformat() if l.created_at else "",
        runtime={
            "model": model_name,
            "fallback_model": fallback_model,
            "max_tokens": max_tokens,
            "timeout_seconds": timeout_seconds,
        },
        price_per_execution=0.05,
        total_executions=0,
    )

def _format_ver_response(v: AgentVersion) -> AgentVersionResponse:
    return AgentVersionResponse(
        id=v.id,
        version_semver=v.version_semver,
        agent_yaml=v.agent_yaml,
        changelog=v.changelog or "",
        status=v.status,
        published_at=v.published_at.isoformat() if v.published_at else ""
    )
