import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default to SQLite file database in the backend/ directory
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./repo_insight.db")

try:
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DATABASE_URL)
except Exception as e:
    print(f"WARNING: Failed to initialize database with URL '{DATABASE_URL}' (Error: {e}). Falling back to local SQLite.")
    DATABASE_URL = "sqlite:///./repo_insight.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency generator to retrieve database sessions in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
