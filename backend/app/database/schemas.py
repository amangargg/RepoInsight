from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- MESSAGE SCHEMAS ---
class ChatMessageBase(BaseModel):
    role: str
    content: str

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageInfo(ChatMessageBase):
    id: str
    session_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- SESSION SCHEMAS ---
class ChatSessionCreate(BaseModel):
    repo_id: str

class ChatSessionInfo(BaseModel):
    id: str
    repo_id: str
    created_at: datetime
    messages: List[ChatMessageInfo] = []

    class Config:
        from_attributes = True


# --- REPORT SCHEMAS ---
class ReviewReportCreate(BaseModel):
    repo_id: str
    type: str
    content: str

class ReviewReportInfo(BaseModel):
    id: str
    repo_id: str
    type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- REPOSITORY SCHEMAS ---
class RepositoryCreate(BaseModel):
    local_path: str
    github_url: Optional[str] = None

class RepositoryInfo(BaseModel):
    id: str
    name: str
    local_path: str
    github_url: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
