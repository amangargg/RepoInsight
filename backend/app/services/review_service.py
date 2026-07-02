from sqlalchemy.orm import Session
from app.database import models
from app.services.agent import CodeAgentManager

class ReviewService:
    @staticmethod
    def run_review(agent_mgr: CodeAgentManager, repo_path: str, db: Session) -> str:
        """Run the review agent over the repository and save the report in the database."""
        report_content = agent_mgr.review_agent.run("")
        
        # Save in database if repository is registered
        db_repo = db.query(models.Repository).filter(models.Repository.local_path == repo_path).first()
        if db_repo:
            db_report = models.ReviewReport(
                repo_id=db_repo.id,
                type="code_review",
                content=report_content
            )
            db.add(db_report)
            db.commit()
            
        return report_content
