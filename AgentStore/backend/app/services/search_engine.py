from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.models.agent_listing import AgentListing
from app.config import settings

try:
    from elasticsearch import Elasticsearch
    es_client = Elasticsearch(settings.ELASTICSEARCH_URL) if settings.USE_ELASTICSEARCH else None
except Exception:
    es_client = None

def index_agent_to_elasticsearch(listing: AgentListing) -> bool:
    if not (settings.USE_ELASTICSEARCH and es_client):
        return False
    try:
        doc = {
            "id": listing.id,
            "slug": listing.slug,
            "name": listing.name,
            "description": listing.description,
            "builder_id": listing.builder_id,
            "category": listing.category,
            "tags": listing.tags or [],
            "capabilities": listing.capabilities or [],
            "trust_score": listing.trust_score,
            "status": listing.status
        }
        es_client.index(index="agents_catalog", id=str(listing.id), document=doc)
        return True
    except Exception:
        return False

def search_agents(
    db: Session,
    q: Optional[str] = None,
    category: Optional[str] = None,
    framework: Optional[str] = None,
    trust_min: Optional[float] = None,
    skip: int = 0,
    limit: int = 20
) -> List[AgentListing]:
    """Search published agents. Attempts Elasticsearch if enabled, falls back to SQL query."""
    
    # Attempt Elasticsearch search if enabled and reachable
    if settings.USE_ELASTICSEARCH and es_client:
        try:
            must_clauses = [{"term": {"status": "active"}}]
            if q:
                must_clauses.append({
                    "multi_match": {
                        "query": q,
                        "fields": ["name^3", "description", "tags^2", "capabilities"]
                    }
                })
            if category and category.lower() != "all":
                must_clauses.append({"term": {"category": category.lower()}})
            if trust_min is not None:
                must_clauses.append({"range": {"trust_score": {"gte": trust_min}}})
                
            res = es_client.search(
                index="agents_catalog",
                query={"bool": {"must": must_clauses}},
                from_=skip,
                size=limit,
                sort=[{"trust_score": {"order": "desc"}}]
            )
            hits = res.get("hits", {}).get("hits", [])
            ids = [int(hit["_id"]) for hit in hits]
            if ids:
                # Fetch ORM objects preserving sort order
                listings_map = {item.id: item for item in db.query(AgentListing).filter(AgentListing.id.in_(ids)).all()}
                return [listings_map[i] for i in ids if i in listings_map]
            return []
        except Exception:
            # Fallback to SQL if ES query fails
            pass

    # SQL fallback query
    query = db.query(AgentListing).filter(AgentListing.status == "active")
    
    if category and category.lower() != "all":
        query = query.filter(AgentListing.category == category.lower())
    
    if trust_min is not None:
        query = query.filter(AgentListing.trust_score >= trust_min)
        
    if q:
        search_term = f"%{q.lower()}%"
        query = query.filter(
            or_(
                AgentListing.name.ilike(search_term),
                AgentListing.description.ilike(search_term),
                AgentListing.slug.ilike(search_term)
            )
        )
        
    # Note: framework filtering in SQL fallback requires inspecting capabilities or JSON array
    if framework and framework.lower() != "all":
        query = query.filter(AgentListing.description.ilike(f"%{framework}%"))
        
    return query.order_by(desc(AgentListing.trust_score), desc(AgentListing.created_at)).offset(skip).limit(limit).all()
