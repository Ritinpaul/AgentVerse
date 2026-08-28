import asyncio
from datetime import UTC, datetime

from database import get_db
from fastapi import APIRouter, Depends
from schemas import (
    EvalResult,
    EvalRunRequest,
    EvalRunResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from services.llm_evaluator import LLMEvaluatorService

router = APIRouter(prefix="/eval", tags=["evaluation"])

@router.post("/run", response_model=EvalRunResponse)
async def run_evaluation(req: EvalRunRequest, db: AsyncSession = Depends(get_db)):
    """
    Run adversarial testing scenarios against the provided agent configuration.
    This simulates policy violations and evaluates if the Sentinel engine correctly blocks them.
    """
    results = []
    total_blocked = 0
    total_failed = 0

    # We use a semaphore to bound the async concurrency to 3 requests at a time.
    semaphore = asyncio.Semaphore(3)

    async def evaluate_single(payload):
        async with semaphore:
            llm_result = await LLMEvaluatorService.evaluate_payload(payload.payload, payload.category)
            
            status = llm_result.get("status", "passed")
            reasoning = llm_result.get("reasoning", "No reasoning provided.")
            policy_triggered = llm_result.get("policy_triggered")
            
            # If the payload was *expected* to be blocked but the LLM passed it, that's a failure of the defense
            if status == "passed" and payload.expected_result == "blocked":
                status = "failed"
                reasoning = f"LLM failed to block adversarial payload. LLM Reasoning: {reasoning}"
                policy_triggered = None
                
            return EvalResult(
                payload_id=payload.id,
                category=payload.category,
                status=status,
                reasoning=reasoning,
                policy_triggered=policy_triggered,
            )

    # Run all evaluations concurrently with semaphore limits
    eval_tasks = [evaluate_single(p) for p in req.payloads]
    results = await asyncio.gather(*eval_tasks)

    for res in results:
        if res.status == "blocked":
            total_blocked += 1
        elif res.status == "failed":
            total_failed += 1

    total_run = len(req.payloads)
    # Calculate a simple compliance score (0 to 1.0)
    score = 1.0 if total_run == 0 else (total_run - total_failed) / total_run

    return EvalRunResponse(
        total_run=total_run,
        total_blocked=total_blocked,
        total_failed=total_failed,
        compliance_score=score,
        results=results,
        timestamp=datetime.now(UTC)
    )
