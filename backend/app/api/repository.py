import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database import models
from app.services.parser import CodebaseParser
from app.services.vector_db import VectorStoreManager
from app.services.agent import CodeAgentManager, session_store
from app.services.github_service import GitHubService

router = APIRouter()

class IngestRequest(BaseModel):
    repo_path: Optional[str] = None
    github_url: Optional[str] = None

@router.post("/ingest")
async def ingest_repository(request: IngestRequest, db: Session = Depends(get_db)):
    """Ingest a repository: supports local paths or Git clone, logs to DB, and indexes."""
    local_path = request.repo_path
    github_url = request.github_url

    # 1. If github_url is provided, clone it
    if github_url:
        try:
            local_path = GitHubService.clone_repository(github_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to clone repository: {str(e)}")

    if not local_path or not os.path.exists(local_path):
        raise HTTPException(status_code=400, detail="Provided local path does not exist.")

    repo_name = os.path.basename(local_path.rstrip("/"))

    # 2. Check if already exists in DB, or create new record
    db_repo = db.query(models.Repository).filter(models.Repository.local_path == local_path).first()
    if not db_repo:
        db_repo = models.Repository(
            name=repo_name,
            local_path=local_path,
            github_url=github_url,
            status="indexing"
        )
        db.add(db_repo)
        db.commit()
        db.refresh(db_repo)

    try:
        # 3. Analyze codebase
        agent_mgr = CodeAgentManager(local_path)
        
        # 4. Generate embeddings and index
        vector_mgr = VectorStoreManager()
        vector_mgr.index_repository(local_path, agent_mgr.repo_report["files"], agent_mgr.parser)
        
        # Save session
        session_store[local_path] = agent_mgr
        
        # Update status in DB
        db_repo.status = "ready"
        db.commit()
        
        return {
            "success": True,
            "message": f"Successfully indexed repository at {local_path}.",
            "repo_id": db_repo.id,
            "name": db_repo.name,
            "repo_path": local_path,
            "summary": agent_mgr.repo_report["summary"],
            "apis": agent_mgr.repo_report["apis"],
            "db_models": agent_mgr.repo_report["db_models"],
            "files": agent_mgr.repo_report["files"]
        }
    except Exception as e:
        db_repo.status = "failed"
        db.commit()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to ingest codebase: {str(e)}")


@router.get("/repositories")
async def list_repositories(db: Session = Depends(get_db)):
    """List all ingested repositories in the database."""
    repos = db.query(models.Repository).all()
    return {
        "success": True,
        "repositories": [
            {
                "id": r.id,
                "name": r.name,
                "local_path": r.local_path,
                "github_url": r.github_url,
                "status": r.status,
                "created_at": r.created_at
            }
            for r in repos
        ]
    }
