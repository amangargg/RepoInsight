from app.agents.orchestrator import OrchestratorAgent
from app.agents.rag_agent import RagAgent
from app.agents.review_agent import ReviewAgent
from app.agents.security_agent import SecurityAgent
from app.agents.documentation_agent import DocumentationAgent
from app.services.parser import CodebaseParser

class CodeAgentManager:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.parser = CodebaseParser(repo_path)
        self.repo_report = self.parser.analyze_repo()
        
        # Initialize orchestrator and worker agents
        self.orchestrator = OrchestratorAgent()
        self.rag_agent = RagAgent(repo_path, self.repo_report)
        self.review_agent = ReviewAgent(repo_path, self.repo_report)
        self.security_agent = SecurityAgent(repo_path, self.repo_report)
        self.doc_agent = DocumentationAgent(repo_path, self.repo_report)

    def answer_question(self, message: str, chat_history: list | None = None) -> str:
        """Route the user query to the appropriate agent worker and run it."""
        try:
            # 1. Ask orchestrator to route request
            category = self.orchestrator.route_request(message)
            print(f"Orchestrator routed request to agent category: '{category}'")

            # 2. Delegate to the correct specialized worker
            if category == "review":
                return self.review_agent.run(message)
            elif category == "security":
                return self.security_agent.run(message)
            elif category == "documentation":
                return self.doc_agent.run(message)
            else:
                return self.rag_agent.run(message, chat_history or [])
        except Exception as exc:
            import traceback
            traceback.print_exc()
# Module level session store to avoid re-parsing on every request
session_store = {}

def get_agent_manager(repo_path: str) -> CodeAgentManager:
    """Helper to retrieve or initialize CodeAgentManager session."""
    import os
    from fastapi import HTTPException
    
    if repo_path in session_store:
        return session_store[repo_path]
        
    if not repo_path or not os.path.exists(repo_path):
        raise HTTPException(status_code=400, detail="Repository folder path does not exist.")
        
    try:
        agent_mgr = CodeAgentManager(repo_path)
        session_store[repo_path] = agent_mgr
        return agent_mgr
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load repository: {str(e)}")
