from app.agents.base import BaseAgent
from app.core.prompts import SECURITY_SYSTEM_PROMPT
from app.services.parser import CodebaseParser

class SecurityAgent(BaseAgent):
    def __init__(self, repo_path: str, repo_report: dict):
        super().__init__()
        self.repo_path = repo_path
        self.repo_report = repo_report
        self.parser = CodebaseParser(repo_path)

    def run(self, message: str) -> str:
        """Scan codebase files and config files for security vulnerabilities."""
        files = self.repo_report.get("files", [])
        if not files:
            return "No files found to audit for security."

        # Prioritize configuration files, env files, and controller/auth files for security scanning
        config_and_source_files = []
        for f in files:
            path = f["path"]
            filename = path.lower().split("/")[-1]
            if (
                filename in ("requirements.txt", "package.json", "dockerfile", "go.mod")
                or any(kw in path.lower() for kw in ("auth", "login", "security", "config", "session", "db"))
            ):
                config_and_source_files.append(f)

        # Fallback to source files if no high-priority config files found
        if len(config_and_source_files) < 2:
            config_and_source_files.extend([
                f for f in files 
                if f.get("language") in ("py", "js", "ts", "java", "go")
            ])

        # Pick top 3-4 files to audit
        audit_targets = config_and_source_files[:4]
        
        security_context_parts = []
        for file_info in audit_targets:
            path = file_info["path"]
            content = self.parser.read_file_safely(path)
            security_context_parts.append(f"--- FILE: {path} ---\n{content[:4000]}")

        security_context = "\n\n".join(security_context_parts)
        prompt = SECURITY_SYSTEM_PROMPT.format(security_context=security_context)
        
        if message:
            prompt += f"\n\nUser specific security query: {message}"
            
        prompt += "\n\nSecurity Audit Output:"
        return self.invoke_llm(prompt)
