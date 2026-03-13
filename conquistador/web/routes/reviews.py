"""Survey/review submission routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from conquistador.models.base import get_db
from conquistador.models.lead import Lead
from conquistador.models.assignment import LeadAssignment
from conquistador.agents.customer_svc import process_survey_submission

router = APIRouter(tags=["reviews"])
templates = Jinja2Templates(directory="templates")


class SurveySubmission(BaseModel):
    on_time_rating: int
    professionalism_rating: int
    problem_solved_rating: int
    comments: str = ""


@router.get("/review/{lead_id}", response_class=HTMLResponse)
async def review_page(request: Request, lead_id: int, token: str = ""):
    return templates.TemplateResponse("review.html", {
        "request": request,
        "lead_id": lead_id,
        "token": token,
    })


@router.post("/api/reviews/{lead_id}")
async def submit_review(
    lead_id: int,
    data: SurveySubmission,
    db: AsyncSession = Depends(get_db),
):
    # Validate ratings are 1-5
    for rating in [data.on_time_rating, data.professionalism_rating, data.problem_solved_rating]:
        if not 1 <= rating <= 5:
            raise HTTPException(status_code=400, detail="Ratings must be between 1 and 5")

    # Find the accepted assignment for this lead
    stmt = (
        select(LeadAssignment)
        .where(LeadAssignment.lead_id == lead_id, LeadAssignment.status == "accepted")
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="No completed service found for this lead")

    review = await process_survey_submission(
        lead_id=lead_id,
        contractor_id=assignment.contractor_id,
        on_time=data.on_time_rating,
        professionalism=data.professionalism_rating,
        problem_solved=data.problem_solved_rating,
        comments=data.comments,
        db=db,
    )

    return {"status": "submitted", "message": "Thank you for your feedback!"}
