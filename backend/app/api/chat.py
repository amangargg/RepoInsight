from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database import models
from app.services.agent import get_agent_manager
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    repo_path: str
    message: str
    history: List[ChatMessage] = []

@router.post("/chat")
async def chat_with_agent(request: ChatRequest, db: Session = Depends(get_db)):
    """Chat with RepoInsight agent, routing requests using multi-agent orchestrator."""
    repo_path = request.repo_path
    agent_mgr = get_agent_manager(repo_path)

    try:
        # Formulate chat history format for LangChain agent
        lc_history = []
        for msg in request.history:
            if msg.role == "user":
                lc_history.append(HumanMessage(content=msg.content))
            else:
                lc_history.append(AIMessage(content=msg.content))

        # Invoke multi-agent system
        answer = agent_mgr.answer_question(request.message, lc_history)
        
        # Save session details in DB
        db_repo = db.query(models.Repository).filter(models.Repository.local_path == repo_path).first()
        if db_repo:
            db_session = db.query(models.ChatSession).filter(models.ChatSession.repo_id == db_repo.id).first()
            if not db_session:
                db_session = models.ChatSession(repo_id=db_repo.id)
                db.add(db_session)
                db.commit()
                db.refresh(db_session)
            
            # Save message logs
            user_msg = models.ChatMessage(session_id=db_session.id, role="user", content=request.message)
            assistant_msg = models.ChatMessage(session_id=db_session.id, role="assistant", content=answer)
            db.add_all([user_msg, assistant_msg])
            db.commit()

        return {
            "success": True,
            "response": answer
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
