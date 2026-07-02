import json
import re
import ast
from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.prompts import RAG_SYSTEM_PROMPT
from app.services.parser import CodebaseParser
from app.services.vector_db import VectorStoreManager

class RagAgent(BaseAgent):
    def __init__(self, repo_path: str, repo_report: dict):
        super().__init__()
        self.repo_path = repo_path
        self.repo_report = repo_report
        self.parser = CodebaseParser(repo_path)
        self.vector_mgr = VectorStoreManager()

    def run(self, message: str, chat_history: list) -> str:
        """Execute Q&A logic using semantic and keyword context."""
        direct_answer = self._answer_from_static_analysis(message)
        matched_files = self._match_requested_files(message)

        if direct_answer and self._should_use_static_answer(message):
            if self.llm:
                grounded_answer = self._answer_static_question_with_llm(message, direct_answer)
                if grounded_answer and not self._looks_ungrounded(grounded_answer):
                    return grounded_answer
            return direct_answer

        if matched_files and self.llm:
            file_answer = self._answer_file_question(message, matched_files)
            if file_answer and not self._looks_ungrounded(file_answer):
                return file_answer
            return self._format_file_static_answer(matched_files)

        # Fallback to general codebase RAG
        is_ollama = settings.LLM_PROVIDER.lower() == "ollama"
        search_results = []
        try:
            n_results = 4 if is_ollama else 8
            search_results = self.vector_mgr.search_codebase(message, n_results=n_results)
        except Exception as exc:
            print(f"WARNING: semantic search failed: {exc}")

        retrieved_context = self._format_search_context(search_results)
        exact_file_context = self._format_exact_file_context(message, max_chars=4000 if is_ollama else 14000)
        keyword_context = self._format_keyword_context(message, max_files=3 if is_ollama else 6)
        
        query_lower = message.lower()
        include_apis = not is_ollama or any(k in query_lower for k in ("api", "route", "endpoint", "url", "http"))
        include_db = not is_ollama or any(k in query_lower for k in ("db", "database", "model", "schema", "table"))

        summary_data = {
            "summary": self.repo_report.get("summary", {})
        }
        if include_apis:
            summary_data["apis"] = self.repo_report.get("apis", [])[:15 if is_ollama else 30]
        if include_db:
            summary_data["db_models"] = self.repo_report.get("db_models", [])[:15 if is_ollama else 30]
            
        summary_data["files"] = [f["path"] for f in self.repo_report.get("files", [])[:15 if is_ollama else 60]]

        parser_context = json.dumps(summary_data, indent=2, default=str)
        static_hint = direct_answer or "No direct static fallback matched this question."
        
        prompt = RAG_SYSTEM_PROMPT.format(
            repo_path=self.repo_path,
            parser_context=parser_context,
            retrieved_context=retrieved_context,
            exact_file_context=exact_file_context,
            keyword_context=keyword_context,
            static_hint=static_hint
        ) + f"\n\nUser Question: {message}\n\nAnswer:"
        
        return self.invoke_llm(prompt)

    def _answer_static_question_with_llm(self, message: str, direct_answer: str) -> str:
        prompt = f"""
You are RepoInsight. The parser has already answered this repository question.
Use the parser answer below as the single source of truth.

Improve the response by:
1. Explaining what it means in plain language.
2. Keeping or adding a small Mermaid diagram when useful.
3. Adding 2-3 practical next steps.

Parser answer:
{direct_answer}

User question:
{message}
"""
        return self.invoke_llm(prompt)

    def _answer_file_question(self, message: str, matched_files: list[str]) -> str:
        exact_file_context = self._format_exact_file_context(message, max_chars=10000)
        prompt = f"""
You are RepoInsight. The user asked about a repository file.
Use only this context. Do not say you lack access.

Answer style:
1. Matched file path
2. Plain-English purpose
3. Main classes/functions and what each does
4. A small Mermaid diagram using graph TD
5. 3 useful follow-up questions

Exact file context:
{exact_file_context}

User question:
{message}
"""
        return self.invoke_llm(prompt)

    def _looks_ungrounded(self, answer: str) -> bool:
        lowered = answer.lower()
        bad_markers = (
            "i don't have access",
            "i do not have access",
            "we don't have access",
            "actual content",
            "simulate",
            "assume",
            "likely part of",
            "appears to be part",
            "model a",
            "model b",
            "provided code snippets"
        )
        return any(marker in lowered for marker in bad_markers)

    def _should_use_static_answer(self, message: str) -> bool:
        question = message.lower()
        return any(
            term in question
            for term in (
                "database", "databas", "db", "schema", "table", "tables", "model", "models",
                "api", "apis", "endpoint", "endpoints", "route", "routes",
                "test", "tests", "testing", "pytest",
                "structure", "overview", "files", "folder",
            )
        )

    def _answer_from_static_analysis(self, message: str) -> str:
        question = message.lower()
        if self._is_model_relationship_question(question):
            return self._format_model_relationship_answer()
        if any(term in question for term in ("database", "databas", "db", "schema", "table", "model")):
            return self._format_db_schema_answer()
        if any(term in question for term in ("api", "apis", "endpoint", "endpoints", "route", "routes")):
            return self._format_api_answer()
        if any(term in question for term in ("auth", "authentication", "login", "register", "registration", "jwt", "token")):
            return self._format_keyword_answer(
                title="Authentication-related code",
                keywords=("auth", "login", "register", "registration", "jwt", "token", "password"),
            )
        if any(term in question for term in ("test", "tests", "testing", "pytest", "jest")):
            return self._format_testing_answer()
        if any(term in question for term in ("structure", "overview", "files", "folder")):
            return self._format_structure_answer()
        return ""

    def _is_model_relationship_question(self, question: str) -> bool:
        models = self.repo_report.get("db_models") or []
        if not models:
            return False
        mentioned_models = [
            model["name"].lower()
            for model in models
            if model.get("name", "").lower() in question
        ]
        relationship_terms = ("work together", "together", "relate", "relationship", "connect", "linked", "flow")
        return len(mentioned_models) >= 2 or (
            bool(mentioned_models) and any(term in question for term in relationship_terms)
        )

    def _format_model_relationship_answer(self) -> str:
        models = self.repo_report.get("db_models") or []
        if not models:
            return self._format_db_schema_answer()

        table_to_model = {
            (model.get("table_name") or self._guess_table_name(model["name"])): model["name"]
            for model in models
        }
        model_names = ", ".join(f"`{model['name']}`" for model in models)
        lines = [
            f"How {model_names} work together:",
            "",
            "RepoInsight is deriving this from the ORM models and foreign keys found in the repository.",
            "",
            "Model roles:",
        ]

        for model in models:
            table_name = model.get("table_name") or self._guess_table_name(model["name"])
            primary_keys = [
                column["name"]
                for column in model.get("columns", [])
                if "primary_key" in (column.get("constraints") or [])
            ]
            foreign_keys = [
                column
                for column in model.get("columns", [])
                if column.get("foreign_key")
            ]
            role_bits = [f"stored in `{table_name}`"]
            if primary_keys:
                role_bits.append(f"identified by `{', '.join(primary_keys)}`")
            if foreign_keys:
                role_bits.append("links to other tables")
            lines.append(f"- `{model['name']}` is {', '.join(role_bits)}.")

        links = []
        for model in models:
            for column in model.get("columns", []):
                foreign_key = column.get("foreign_key")
                if not foreign_key or "." not in foreign_key:
                    continue
                target_table, target_column = foreign_key.split(".", 1)
                target_model = table_to_model.get(target_table, target_table)
                links.append((model["name"], column["name"], target_model, target_column))

        if links:
            lines.extend(["", "Data relationships:"])
            for source_model, source_column, target_model, target_column in links:
                lines.append(
                    f"- `{source_model}.{source_column}` points to `{target_model}.{target_column}`."
                )

        return "\n".join(lines)

    def _format_db_schema_answer(self) -> str:
        models = self.repo_report.get("db_models") or []
        if not models:
            return "No database tables or ORM models were detected."

        lines = [
            "Database schema overview:",
            "",
            f"RepoInsight detected {len(models)} database model(s).",
        ]
        for model in models:
            table_name = model.get("table_name") or self._guess_table_name(model["name"])
            lines.extend([
                "",
                f"### `{model['name']}`",
                f"- Table: `{table_name}`",
                f"- Source: `{model['file']}` line {model['line']}",
            ])
        return "\n".join(lines)

    def _format_api_answer(self) -> str:
        apis = self.repo_report.get("apis") or []
        if not apis:
            return "No API routes were detected."

        lines = ["Detected API routes:"]
        for api in apis:
            lines.append(
                f"- `{api['method']} {api['path']}` handled by `{api['handler']}` in `{api['file']}` line {api['line']}"
            )
        return "\n".join(lines)

    def _format_testing_answer(self) -> str:
        files = self.repo_report.get("files") or []
        test_files = [f for f in files if "test" in f["path"].lower()]
        if not test_files:
            return "No test suite detected in the codebase."
        return f"Detected test files: " + ", ".join(f"`{f['path']}`" for f in test_files[:10])

    def _format_structure_answer(self) -> str:
        summary = self.repo_report.get("summary") or {}
        return (
            f"Repository overview:\n"
            f"- Total files: {summary.get('total_files', 0)}\n"
            f"- Total lines: {summary.get('total_lines', 0)}\n"
        )

    def _format_keyword_answer(self, title: str, keywords: tuple[str, ...]) -> str:
        matches = []
        for file_info in self.repo_report.get("files", []):
            rel_path = file_info["path"]
            content = self.parser.read_file_safely(rel_path)
            for line_number, line in enumerate(content.splitlines(), start=1):
                if any(keyword in line.lower() for keyword in keywords):
                    matches.append((rel_path, line_number, line.strip()))
                    break
            if len(matches) >= 5:
                break
        if not matches:
            return f"No obvious {title.lower()} references found."
        lines = [f"{title} references found in:"]
        for path, line, snippet in matches:
            lines.append(f"- `{path}` line {line}: `{snippet[:120]}`")
        return "\n".join(lines)

    def _guess_table_name(self, model_name: str) -> str:
        return model_name.lower() + "s"

    def _format_search_context(self, search_results: list[dict]) -> str:
        if not search_results:
            return "No semantic search results were available."
        parts = []
        for result in search_results:
            if isinstance(result, dict):
                parts.append(
                    "\n".join([
                        f"FILE: {result.get('file_path', 'unknown')}",
                        f"LINES: {result.get('start_line', '?')}-{result.get('end_line', '?')}",
                        "CONTENT:",
                        result.get("content", ""),
                    ])
                )
            else:
                parts.append(str(result))
        return "\n\n---\n\n".join(parts)

    def _format_exact_file_context(self, query: str, max_chars: int = 14000) -> str:
        matched_paths = self._match_requested_files(query)
        if not matched_paths:
            return "No exact file requested or matched."
        parts = []
        for rel_path in matched_paths[:2]:
            content = self.parser.read_file_safely(rel_path)
            parts.append(f"FILE: {rel_path}\nCONTENT:\n{content[:max_chars]}")
        return "\n\n---\n\n".join(parts)

    def _match_requested_files(self, query: str) -> list[str]:
        normalized_query = query.lower()
        requested = set(re.findall(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+", normalized_query))
        if not requested:
            return []
        matches = []
        for file_info in self.repo_report.get("files", []):
            path = file_info["path"]
            if any(name in path.lower() for name in requested):
                matches.append(path)
        return matches

    def _format_file_static_answer(self, matched_files: list[str]) -> str:
        rel_path = matched_files[0]
        content = self.parser.read_file_safely(rel_path)
        return f"File details for `{rel_path}`:\n```\n{content[:2000]}\n```"

    def _format_keyword_context(self, query: str, max_files: int = 6) -> str:
        return "No specific keyword matches extracted."
