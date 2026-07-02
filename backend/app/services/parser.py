import os
import ast
import re

# Standard folders to ignore when crawling codebase
IGNORED_DIRS = {
    '.git', 'node_modules', 'venv', '.venv', '__pycache__', 'dist', 
    'build', '.next', '.nuxt', 'out', 'target', 'bin', 'obj', '.agents',
    '.pytest_cache', '.mypy_cache', '.ruff_cache', 'repositories', 'chroma_db'
}

# Standard extensions to ignore (binary and lock files)
IGNORED_EXTS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf', '.zip', 
    '.tar', '.gz', '.db', '.sqlite', '.sqlite3', '.exe', '.dll', '.so', '.dylib', 
    '.woff', '.woff2', '.eot', '.ttf', '.mp3', '.mp4', '.avi',
    '.DS_Store', '.env', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock'
}

def should_ignore(path: str) -> bool:
    """Check if the file or directory should be ignored."""
    parts = path.split(os.sep)
    for part in parts:
        if part in IGNORED_DIRS:
            return True
    
    filename = os.path.basename(path)
    if filename in IGNORED_EXTS:
        return True
    
    _, ext = os.path.splitext(filename)
    if ext in IGNORED_EXTS:
        return True
        
    return False

class CodebaseParser:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)

    def _node_name(self, node) -> str:
        """Return a readable name for AST Name/Attribute/Call nodes."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._node_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        if isinstance(node, ast.Call):
            return self._node_name(node.func)
        if isinstance(node, ast.Subscript):
            return self._node_name(node.value)
        return ""

    def _literal_value(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        return None

    def _extract_call_details(self, node: ast.Call) -> dict:
        args = []
        keywords = {}

        for arg in node.args:
            literal = self._literal_value(arg)
            args.append(literal if literal is not None else self._node_name(arg))

        for keyword in node.keywords:
            if keyword.arg:
                literal = self._literal_value(keyword.value)
                keywords[keyword.arg] = literal if literal is not None else self._node_name(keyword.value)

        return {
            "function": self._node_name(node.func),
            "args": args,
            "keywords": keywords
        }

    def _extract_model_details(self, node: ast.ClassDef) -> dict:
        """Extract table, columns, and relationships from a Python ORM model."""
        table_name = ""
        columns = []
        relationships = []

        for stmt in node.body:
            if not isinstance(stmt, ast.Assign) or not stmt.targets:
                continue

            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue

            attr_name = target.id
            if attr_name == "__tablename__":
                literal = self._literal_value(stmt.value)
                table_name = str(literal) if literal is not None else ""
                continue

            if not isinstance(stmt.value, ast.Call):
                continue

            call = self._extract_call_details(stmt.value)
            function_name = call["function"].split(".")[-1]

            if function_name in {"Column", "mapped_column"}:
                column_type = ""
                foreign_key = ""
                constraints = []

                for arg in call["args"]:
                    if isinstance(arg, str) and arg.startswith(("ForeignKey", "sqlalchemy.ForeignKey")):
                        foreign_key = arg
                    elif isinstance(arg, str) and "." in arg and not column_type:
                        column_type = arg.split(".")[-1]
                    elif isinstance(arg, str) and arg and not column_type:
                        column_type = arg

                for nested in ast.walk(stmt.value):
                    if isinstance(nested, ast.Call) and self._node_name(nested.func).split(".")[-1] == "ForeignKey":
                        nested_details = self._extract_call_details(nested)
                        if nested_details["args"]:
                            foreign_key = str(nested_details["args"][0])

                for key, value in call["keywords"].items():
                    if value is True:
                        constraints.append(key)
                    elif value not in (False, None, ""):
                        constraints.append(f"{key}={value}")

                columns.append({
                    "name": attr_name,
                    "type": column_type or "unknown",
                    "foreign_key": foreign_key,
                    "constraints": constraints,
                    "line": stmt.lineno
                })

            elif function_name == "relationship":
                target_model = str(call["args"][0]) if call["args"] else "unknown"
                relationships.append({
                    "name": attr_name,
                    "target": target_model,
                    "options": call["keywords"],
                    "line": stmt.lineno
                })

        return {
            "table_name": table_name,
            "columns": columns,
            "relationships": relationships
        }

    def crawl_files(self) -> list[str]:
        """Walk the repository and return relative file paths."""
        file_list = []
        for root, dirs, files in os.walk(self.repo_path):
            # Prune ignored directories in-place so os.walk doesn't go into them
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.repo_path)
                if not should_ignore(rel_path):
                    file_list.append(rel_path)
        return file_list

    def read_file_safely(self, rel_path: str) -> str:
        """Read a file's content safely supporting common encodings."""
        from app.utils.file_loader import read_file_safely as loader_read
        full_path = os.path.join(self.repo_path, rel_path)
        return loader_read(full_path)

    def parse_python_ast(self, content: str, rel_path: str) -> dict:
        """Parse Python code using AST to extract classes, functions, and metadata."""
        result = {
            "classes": [],
            "functions": [],
            "apis": [],
            "db_models": []
        }
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return result  # Return empty if invalid Python code

        for node in ast.walk(tree):
            # 1. Classes
            if isinstance(node, ast.ClassDef):
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)

                class_info = {
                    "name": node.name,
                    "bases": base_names,
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                    "docstring": ast.get_docstring(node) or ""
                }
                result["classes"].append(class_info)
                
                # Identify potential DB models (e.g. SQLAlchemy, SQLModel, Django models)
                db_keywords = {'Base', 'Model', 'SQLModel', 'db.Model'}
                pydantic_bases = {'BaseModel'}
                is_pydantic_schema = any(base in pydantic_bases for base in base_names)
                is_db_model = (
                    any(kw in base_names for kw in db_keywords)
                    or any('model' in base.lower() for base in base_names)
                )
                if is_db_model and not is_pydantic_schema:
                    model_details = self._extract_model_details(node)
                    result["db_models"].append({
                        "name": node.name,
                        "type": "ORM Model",
                        "file": rel_path,
                        "line": node.lineno,
                        **model_details
                    })

            # 2. Functions & Methods
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = {
                    "name": node.name,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "line_start": node.lineno,
                    "line_end": getattr(node, "end_lineno", node.lineno),
                    "docstring": ast.get_docstring(node) or ""
                }
                result["functions"].append(func_info)

                # Check decorators for API endpoints (e.g. @app.get, @router.post)
                for decorator in node.decorator_list:
                    decorator_str = ""
                    if isinstance(decorator, ast.Call):
                        decorator_node = decorator.func
                    else:
                        decorator_node = decorator

                    if isinstance(decorator_node, ast.Attribute):
                        decorator_str = f"{getattr(decorator_node.value, 'id', '')}.{decorator_node.attr}"
                    elif isinstance(decorator_node, ast.Name):
                        decorator_str = decorator_node.id

                    # Typical web framework endpoint markers (FastAPI, Flask, etc.)
                    if any(marker in decorator_str.lower() for marker in ['get', 'post', 'put', 'delete', 'patch', 'route']):
                        # Try to extract the path (first argument of the decorator call)
                        route_path = "unknown"
                        if isinstance(decorator, ast.Call) and decorator.args:
                            first_arg = decorator.args[0]
                            if isinstance(first_arg, ast.Constant):
                                route_path = str(first_arg.value)
                        
                        result["apis"].append({
                            "method": decorator_str.split('.')[-1].upper(),
                            "path": route_path,
                            "handler": node.name,
                            "file": rel_path,
                            "line": node.lineno
                        })

        return result

    def parse_regex_signatures(self, content: str, rel_path: str) -> dict:
        """Regex-based parser for non-Python or general codebases (Express, Prisma, SQL, etc.)."""
        result = {
            "apis": [],
            "db_models": []
        }
        
        _, ext = os.path.splitext(rel_path)
        ext = ext.lower()

        # 1. Look for Express / Node.js Router endpoints
        # Matches: router.get('/path', ...), app.post("/path", ...)
        express_matches = re.finditer(
            r'(?:app|router|route)\.(get|post|put|delete|patch)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]', 
            content, 
            re.IGNORECASE
        )
        for match in express_matches:
            method = match.group(1).upper()
            path = match.group(2)
            # Find line number
            line_no = content.count('\n', 0, match.start()) + 1
            result["apis"].append({
                "method": method,
                "path": path,
                "handler": "anonymous",
                "file": rel_path,
                "line": line_no
            })

        # 2. Look for Spring Boot API signatures (Java)
        # Matches: @GetMapping("/path"), @PostMapping(value = "/path")
        spring_matches = re.finditer(
            r'@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?[\'"`]([^\'"`]+)[\'"`]',
            content
        )
        for match in spring_matches:
            method = match.group(1).upper()
            path = match.group(2)
            line_no = content.count('\n', 0, match.start()) + 1
            result["apis"].append({
                "method": method,
                "path": path,
                "handler": "Spring Controller",
                "file": rel_path,
                "line": line_no
            })

        # 3. Look for Prisma Schema DB Models
        if ext == '.prisma':
            prisma_matches = re.finditer(r'model\s+(\w+)\s*\{', content)
            for match in prisma_matches:
                model_name = match.group(1)
                line_no = content.count('\n', 0, match.start()) + 1
                result["db_models"].append({
                    "name": model_name,
                    "type": "Prisma Model",
                    "file": rel_path,
                    "line": line_no
                })
        
        # 4. Look for raw SQL CREATE TABLE
        if ext in ('.sql', '.ddl'):
            sql_matches = re.finditer(r'create\s+table\s+(\w+)', content, re.IGNORECASE)
            for match in sql_matches:
                table_name = match.group(1)
                line_no = content.count('\n', 0, match.start()) + 1
                result["db_models"].append({
                    "name": table_name,
                    "type": "SQL Table",
                    "file": rel_path,
                    "line": line_no
                })

        return result

    def parse_python_imports(self, content: str, rel_path: str, all_files: list[str]) -> list[str]:
        """Extract import statements from Python files and resolve them to local files."""
        imports = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
                
        resolved = []
        for imp in imports:
            imp_path = imp.replace(".", "/")
            for file_path in all_files:
                base_file_path, _ = os.path.splitext(file_path)
                if base_file_path == imp_path or base_file_path.endswith("/" + imp_path) or imp_path.endswith(base_file_path):
                    if file_path != rel_path:
                        resolved.append(file_path)
                        break
        return list(set(resolved))

    def parse_js_imports(self, content: str, rel_path: str, all_files: list[str]) -> list[str]:
        """Regex-based import parser for JS/TS ES Modules imports."""
        imports = []
        matches = re.finditer(r'import\s+(?:[^"\';]+\s+from\s+)?[\'"]([^\'"]+)[\'"]', content)
        for match in matches:
            imports.append(match.group(1))
            
        resolved = []
        for imp in imports:
            if imp.startswith((".", "/")):
                dir_path = os.path.dirname(rel_path)
                target_rel = os.path.normpath(os.path.join(dir_path, imp))
                for file_path in all_files:
                    base_file_path, _ = os.path.splitext(file_path)
                    if base_file_path == target_rel or base_file_path.endswith(target_rel):
                        if file_path != rel_path:
                            resolved.append(file_path)
                            break
            else:
                clean_imp = imp.replace("@/", "src/")
                for file_path in all_files:
                    base_file_path, _ = os.path.splitext(file_path)
                    if base_file_path == clean_imp or base_file_path.endswith(clean_imp):
                        if file_path != rel_path:
                            resolved.append(file_path)
                            break
        return list(set(resolved))

    def analyze_repo(self) -> dict:
        """Run parser over the whole repo and collect structures."""
        files = self.crawl_files()
        report = {
            "files": [],
            "apis": [],
            "db_models": [],
            "summary": {
                "total_files": len(files),
                "languages": {},
                "total_lines": 0
            }
        }

        for rel_path in files:
            content = self.read_file_safely(rel_path)
            lines = content.count('\n') + 1
            report["summary"]["total_lines"] += lines

            _, ext = os.path.splitext(rel_path)
            ext = ext.lstrip('.').lower() or 'text'
            report["summary"]["languages"][ext] = report["summary"]["languages"].get(ext, 0) + 1

            file_info = {
                "path": rel_path,
                "lines": lines,
                "language": ext
            }
            
            # Extract imports dependencies
            file_imports = []
            if ext == 'py':
                file_imports = self.parse_python_imports(content, rel_path, files)
            elif ext in ('js', 'jsx', 'ts', 'tsx'):
                file_imports = self.parse_js_imports(content, rel_path, files)
            file_info["imports"] = file_imports
            
            # Extract structures based on file extension
            if ext == 'py':
                ast_data = self.parse_python_ast(content, rel_path)
                report["apis"].extend(ast_data["apis"])
                report["db_models"].extend(ast_data["db_models"])
                file_info.update({
                    "classes": [c["name"] for c in ast_data["classes"]],
                    "functions": [f["name"] for f in ast_data["functions"]]
                })
            else:
                regex_data = self.parse_regex_signatures(content, rel_path)
                report["apis"].extend(regex_data["apis"])
                report["db_models"].extend(regex_data["db_models"])

            report["files"].append(file_info)

        return report
