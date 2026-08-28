"""
CrewAI Engine — FastAPI wrapper for agent orchestration.

Exposes endpoints to trigger dispute resolution and meta governance sweeps.
Communicates with the Governance API for trust scoring, policy checks, and auditing.
"""

from contextlib import asynccontextmanager

from crews.dispute_crew import DisputeResolutionCrew
from crews.meta_crew import MetaGovernanceCrew
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize crews on startup."""
    app.state.dispute_crew = DisputeResolutionCrew()
    app.state.meta_crew = MetaGovernanceCrew()
    yield


app = FastAPI(
    title="AgentGovern OS — CrewAI Engine",
    description="9-agent orchestration engine for dispute resolution and governance oversight.",
    version="0.1.0",
    lifespan=lifespan,
)


class DisputeRequest(BaseModel):
    dispute_id: str = Field(..., examples=["DISP-2024-7749"])
    customer_id: str = Field(..., examples=["CUST-001"])
    description: str = Field(..., examples=["Invoice amount mismatch for PO-45231"])
    amount: float = Field(..., examples=[25000.00])
    currency: str = Field(default="INR")
    dispute_type: str = Field(default="invoice_mismatch")
    context: dict = Field(default_factory=dict)


class CrewResult(BaseModel):
    status: str
    result: dict
    agents_used: int
    crew_type: str


@app.post("/resolve", response_model=CrewResult)
async def resolve_dispute(request: DisputeRequest):
    """Trigger the Core Crew to resolve a dispute."""
    try:
        result = await app.state.dispute_crew.resolve(request.model_dump())
        return CrewResult(
            status="completed",
            result=result,
            agents_used=5,
            crew_type="dispute_resolution",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crew execution failed: {e!s}")


@app.post("/meta/daily")
async def run_daily_check():
    """Trigger the daily fleet health check (Historian)."""
    crew = app.state.meta_crew.build_daily_check_crew()
    result = crew.kickoff()
    return {"status": "completed", "type": "daily_check", "result": str(result)}


@app.post("/meta/weekly")
async def run_weekly_sweep():
    """Trigger the full weekly governance sweep (all 4 Meta agents)."""
    crew = app.state.meta_crew.build_weekly_sweep_crew()
    result = crew.kickoff()
    return {"status": "completed", "type": "weekly_sweep", "result": str(result)}


@app.post("/meta/redteam")
async def run_red_team():
    """Trigger an adversarial red team probe."""
    crew = app.state.meta_crew.build_red_team_crew()
    result = crew.kickoff()
    return {"status": "completed", "type": "red_team_probe", "result": str(result)}


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "crewai", "agents": 9}
