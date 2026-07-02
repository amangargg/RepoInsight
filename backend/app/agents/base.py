from app.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None

class BaseAgent:
    def __init__(self):
        self.llm = self._init_llm()

    def _init_llm(self):
        """Initialize the LLM based on LLM_PROVIDER settings."""
        provider = settings.LLM_PROVIDER.lower()

        if provider == "ollama":
            if ChatOllama is None:
                print("WARNING: langchain-ollama is not installed. Local LLM is disabled.")
                return None
            return ChatOllama(
                model=settings.OLLAMA_MODEL,
                temperature=0.2
            )

        if provider == "gemini":
            api_key = settings.GEMINI_API_KEY
            if api_key and api_key != "your_gemini_api_key_here":
                return ChatGoogleGenerativeAI(
                    model=settings.GEMINI_CHAT_MODEL,
                    google_api_key=api_key,
                    temperature=0.2,
                    transport="rest",
                    max_retries=1
                )
            print("WARNING: GEMINI_API_KEY is not set. Gemini is disabled.")
            return None

        print("WARNING: Unknown LLM provider. LLM is disabled.")
        return None

    def invoke_llm(self, prompt: str) -> str:
        """Invoke the LLM defensively, converting any output to a string."""
        if not self.llm:
            return "AI model is not configured. Please set your credentials/provider."
        try:
            response = self.llm.invoke(prompt)
            return self._stringify_output(getattr(response, "content", response))
        except Exception as e:
            return f"Error executing LLM call: {e}"

    def _stringify_output(self, output) -> str:
        if isinstance(output, str):
            return output
        if hasattr(output, "content"):
            return str(output.content)
        if isinstance(output, list):
            parts = []
            for item in output:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or item))
                elif isinstance(item, str):
                    parts.append(item)
                elif hasattr(item, "content"):
                    parts.append(str(item.content))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(output)
