from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.agent import get_agent_manager
from app.services.review_service import ReviewService

router = APIRouter()

class ReportRequest(BaseModel):
    repo_path: str

@router.post("/review")
async def get_code_review(request: ReportRequest, db: Session = Depends(get_db)):
    """Trigger specialized Code Review Agent to inspect repository quality."""
    repo_path = request.repo_path
    agent_mgr = get_agent_manager(repo_path)

    try:
        report_content = ReviewService.run_review(agent_mgr, repo_path, db)
        return {
            "success": True,
            "report": report_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code review failed: {str(e)}")
