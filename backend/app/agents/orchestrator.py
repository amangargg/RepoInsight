from app.agents.base import BaseAgent
from app.core.prompts import ORCHESTRATOR_SYSTEM_PROMPT

class OrchestratorAgent(BaseAgent):
    def route_request(self, user_message: str) -> str:
        """Classifies user intent and routes it to the correct specialized worker agent."""
        if not self.llm:
            # Safe default fallback
            return "rag"
            
        prompt = f"{ORCHESTRATOR_SYSTEM_PROMPT}\n\nUser Question: {user_message}\n\nSelected Category:"
        
        # We want to keep routing fast and simple
        try:
            response = self.invoke_llm(prompt).strip().lower()
            
            # Clean up response (some models might add quotes or extra words)
            for category in ["rag", "review", "security", "documentation"]:
                if category in response:
                    return category
                    
            return "rag"  # Fallback if unresolvable
        except Exception:
            return "rag"
