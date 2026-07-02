import os
os.environ["ANON_TELEMETRY"] = "False"

import logging
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Initialize Database tables
from app.database.session import Base, engine
from app.database import models
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RepoInsight API",
    description="Backend service for code ingestion, static analysis, and AI Q&A agent.",
    version="0.2.0"
)

# Import and include sub-routers
from app.api.repository import router as repository_router
from app.api.chat import router as chat_router
from app.api.review import router as review_router
from app.api.security import router as security_router
from app.api.upload import router as upload_router

app.include_router(repository_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(security_router, prefix="/api")
app.include_router(upload_router, prefix="/api")

# Set up CORS middleware to allow communication with frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "RepoInsight Multi-Agent API",
        "version": "0.2.0"
    }
