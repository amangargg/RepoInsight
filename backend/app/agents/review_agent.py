from app.agents.base import BaseAgent
from app.core.prompts import REVIEW_SYSTEM_PROMPT
from app.services.parser import CodebaseParser

class ReviewAgent(BaseAgent):
    def __init__(self, repo_path: str, repo_report: dict):
        super().__init__()
        self.repo_path = repo_path
        self.repo_report = repo_report
        self.parser = CodebaseParser(repo_path)

    def run(self, message: str) -> str:
        """Scan the repository files and generate a structured Code Quality Review."""
        # Find files matching the request, or default to reviewing the primary source files
        files = self.repo_report.get("files", [])
        if not files:
            return "No files found to review in this repository."

        # Filter files to python, js, ts files (avoid review of configs/images)
        target_files = [
            f for f in files 
            if f.get("language") in ("py", "js", "jsx", "ts", "tsx", "java", "go")
        ]
        if not target_files:
            target_files = files

        # Pick top 3 files to keep prompt within token limits for local LLMs
        review_targets = target_files[:3]
        
        review_context_parts = []
        for file_info in review_targets:
            path = file_info["path"]
            content = self.parser.read_file_safely(path)
            # Limit file length to prevent prompt overflow
            review_context_parts.append(f"--- FILE: {path} ---\n{content[:4000]}")

        review_context = "\n\n".join(review_context_parts)
        prompt = REVIEW_SYSTEM_PROMPT.format(review_context=review_context)
        
        if message:
            prompt += f"\n\nUser specific review request: {message}"
            
        prompt += "\n\nReview Output:"
        return self.invoke_llm(prompt)
