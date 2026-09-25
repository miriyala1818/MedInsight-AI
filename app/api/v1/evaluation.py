from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_evaluation_service
from app.schemas.evaluation import EvaluationDashboardResponse, EvaluationRunInput
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation")


@router.get("/dashboard", response_model=EvaluationDashboardResponse, summary="Evaluation dashboard metrics")
async def get_dashboard_metrics(
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationDashboardResponse:
    return service.empty_dashboard()


@router.post("/run", summary="Calculate evaluation metrics from a single run")
async def post_run_metrics(
    payload: EvaluationRunInput,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, float | str]:
    return service.calculate_from_input(payload)
