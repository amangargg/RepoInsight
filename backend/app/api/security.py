from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.agent import get_agent_manager
from app.services.security_service import SecurityService

router = APIRouter()

class ReportRequest(BaseModel):
    repo_path: str

@router.post("/security")
async def get_security_audit(request: ReportRequest, db: Session = Depends(get_db)):
    """Trigger specialized Security Agent to inspect repository vulnerabilities."""
    repo_path = request.repo_path
    agent_mgr = get_agent_manager(repo_path)

    try:
        report_content = SecurityService.run_security_audit(agent_mgr, repo_path, db)
        return {
            "success": True,
            "report": report_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Security audit failed: {str(e)}")
