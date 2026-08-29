from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.services.search_engine import search_agents
from app.routers.registry import AgentListingResponse, _format_listing_response

router = APIRouter(prefix="/search", tags=["Search Engine"])

@router.get("", response_model=List[AgentListingResponse])
def search_catalog(
    q: Optional[str] = Query(None, description="Keyword search query"),
    category: Optional[str] = Query("all", description="Filter by category"),
    framework: Optional[str] = Query("all", description="Filter by framework"),
    trust_min: Optional[float] = Query(None, ge=0, le=100, description="Minimum trust score"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    results = search_agents(
        db=db,
        q=q,
        category=category,
        framework=framework,
        trust_min=trust_min,
        skip=skip,
        limit=limit
    )
    return [_format_listing_response(item) for item in results]
