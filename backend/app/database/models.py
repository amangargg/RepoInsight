import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    local_path = Column(String, unique=True, nullable=False)
    github_url = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, indexing, ready, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reports = relationship("ReviewReport", back_populates="repository", cascade="all, delete-orphan")
    sessions = relationship("ChatSession", back_populates="repository", cascade="all, delete-orphan")


class ReviewReport(Base):
    __tablename__ = "review_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    repo_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    type = Column(String, default="general")  # code_review, security_audit, doc_check
    content = Column(Text, nullable=False)  # Markdown text response
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="reports")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    repo_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
