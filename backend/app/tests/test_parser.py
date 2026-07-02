import os
from app.services.parser import CodebaseParser

def test_codebase_crawler():
    # Crawl the backend directory itself
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser = CodebaseParser(current_dir)
    files = parser.crawl_files()
    
    # Assert we find Python files and requirements.txt
    assert "app/main.py" in files
    assert "requirements.txt" in files
    
    # Assert we did not crawl ignored directories (like venv if it's there)
    for f in files:
        assert "venv" not in f.split(os.sep)
        assert "__pycache__" not in f.split(os.sep)

def test_python_ast_parser():
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser = CodebaseParser(current_dir)
    
    # Find app/main.py
    main_path = "app/main.py"
    content = parser.read_file_safely(main_path)
    
    assert content != ""
    
    parsed_data = parser.parse_python_ast(content, main_path)
    
    # Should find the root API endpoint function
    func_names = [f["name"] for f in parsed_data["functions"]]
    assert "root" in func_names
    
    # Should find root API endpoint in apis
    api_paths = [a["path"] for a in parsed_data["apis"]]
    assert "/" in api_paths

def test_repo_analyzer_summary():
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser = CodebaseParser(current_dir)
    report = parser.analyze_repo()
    
    # Verify summary structure
    assert "summary" in report
    assert report["summary"]["total_files"] > 0
    assert "py" in report["summary"]["languages"]
    
    # Verify detected endpoints (FastAPI router endpoints)
    apis = report["apis"]
    assert len(apis) > 0
    
    # Verify at least the main router endpoints are detected
    api_paths = [a["path"] for a in apis]
    assert "/api/ingest" in api_paths or "ingest" in "".join(api_paths)

def test_sqlalchemy_model_details():
    content = '''
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User", back_populates="posts")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
'''
    parser = CodebaseParser("/tmp")
    parsed_data = parser.parse_python_ast(content, "app/models.py")

    models = {model["name"]: model for model in parsed_data["db_models"]}
    assert set(models) == {"Post", "User"}
    assert models["Post"]["table_name"] == "posts"
    assert models["Post"]["columns"][0]["name"] == "id"
    assert "primary_key" in models["Post"]["columns"][0]["constraints"]
    assert models["Post"]["columns"][2]["foreign_key"] == "users.id"
    assert models["Post"]["relationships"][0]["target"] == "User"
