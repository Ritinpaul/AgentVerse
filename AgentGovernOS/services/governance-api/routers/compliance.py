"""
Compliance Router

Endpoints to generate, fetch, and verify compliance reports 
(e.g., EU AI Act, ISO 42001) for the AgentGovernOS ecosystem.
"""

import uuid

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.compliance.compliance_reporter import ComplianceReporter

router = APIRouter(prefix="/compliance", tags=["Compliance"])
reporter = ComplianceReporter

class ReportRequest(BaseModel):
    framework: str # 'eu_ai_act', 'iso_42001'
    scope: str = "global"

class ReportResponse(BaseModel):
    id: str
    framework: str
    markdown_content: str


@router.post("/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_compliance_report(req: ReportRequest, db: AsyncSession = Depends(get_db)):
    """
    Generates a compliance report evidence package based on the immutable ledger.
    """
    try:
        content = await reporter.generate_report(framework=req.framework, db=db, scope=req.scope)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    report_id = str(uuid.uuid4)
    
    # In a full implementation, we'd save this report to the DB/S3.
    # For now, we return it synchronously.
    
    return ReportResponse(
        id=report_id,
        framework=req.framework,
        markdown_content=content
    )


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_compliance_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves a previously generated compliance report.
    (Mocked)
    """
    raise HTTPException(status_code=404, detail="Not implemented in demo")
