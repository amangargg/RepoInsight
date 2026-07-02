from app.agents.base import BaseAgent
from app.core.prompts import DOCUMENTATION_SYSTEM_PROMPT
from app.services.parser import CodebaseParser

class DocumentationAgent(BaseAgent):
    def __init__(self, repo_path: str, repo_report: dict):
        super().__init__()
        self.repo_path = repo_path
        self.repo_report = repo_report
        self.parser = CodebaseParser(repo_path)

    def run(self, message: str) -> str:
        """Analyze files and write clean technical documentation."""
        files = self.repo_report.get("files", [])
        if not files:
            return "No files found to generate documentation for."

        # Scan for matching files in user query, otherwise default to core backend files
        matched_targets = []
        for f in files:
            if f["path"].lower() in message.lower() or f["path"].split("/")[-1].lower() in message.lower():
                matched_targets.append(f)
                
        if not matched_targets:
            matched_targets = [
                f for f in files 
                if f.get("language") in ("py", "js", "ts", "java")
            ][:3]

        doc_context_parts = []
        for file_info in matched_targets:
            path = file_info["path"]
            content = self.parser.read_file_safely(path)
            doc_context_parts.append(f"--- FILE: {path} ---\n{content[:4000]}")

        doc_context = "\n\n".join(doc_context_parts)
        prompt = DOCUMENTATION_SYSTEM_PROMPT.format(doc_context=doc_context)
        
        if message:
            prompt += f"\n\nUser specific documentation request: {message}"
            
        prompt += "\n\nDocumentation Output:"
        return self.invoke_llm(prompt)
