import os
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from app.core.config import settings
from app.services.embedding_service import get_embeddings_provider
from chromadb.config import Settings as ChromaSettings

class VectorStoreManager:
    def __init__(self):
        self.embeddings = get_embeddings_provider()

    def get_chroma_db(self, collection_name: str = "repo_insight_code") -> Chroma:
        """Get or create ChromaDB instance."""
        if not self.embeddings:
            raise ValueError("Embeddings could not be initialized.")
        
        persist_dir = settings.CHROMA_DB_PATH
        os.makedirs(persist_dir, exist_ok=True)
        
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_dir,
            client_settings=ChromaSettings(anonymized_telemetry=False)
        )

    def chunk_and_index_file(self, db: Chroma, file_path: str, content: str, language: str):
        """Split a code file into semantic chunks and store them in ChromaDB."""
        if not content.strip():
            return
            
        from app.utils.chunking import get_splitter_for_language
        splitter = get_splitter_for_language(language)

        chunks = splitter.create_documents(
            texts=[content],
            metadatas=[{
                "file_path": file_path,
                "language": language
            }]
        )
        
        # Inject line numbering metadata
        for i, chunk in enumerate(chunks):
            search_text = chunk.page_content[:100]
            start_index = content.find(search_text)
            if start_index != -1:
                start_line = content.count('\n', 0, start_index) + 1
            else:
                start_line = 1
                
            chunk.metadata["start_line"] = start_line
            chunk.metadata["end_line"] = start_line + chunk.page_content.count('\n')
            chunk.metadata["chunk_index"] = i

        if chunks:
            # Index in batches of 16 to avoid API timeouts on large files
            batch_size = 16
            for idx in range(0, len(chunks), batch_size):
                db.add_documents(chunks[idx:idx + batch_size])

    def index_repository(self, repo_path: str, files_report: list[dict], parser_instance):
        """Index all files of a crawled repository into the vector database."""
        db = self.get_chroma_db()
        
        # Clear existing collection first if it exists to refresh indexing
        try:
            db.delete_collection()
            db = self.get_chroma_db()
        except Exception:
            pass

        indexed = 0
        skipped = 0
        for i, file_info in enumerate(files_report):
            rel_path = file_info["path"]
            lang = file_info["language"]
            content = parser_instance.read_file_safely(rel_path)
            try:
                self.chunk_and_index_file(db, rel_path, content, lang)
                indexed += 1
                print(f"  [{i+1}/{len(files_report)}] Indexed: {rel_path}")
            except Exception as e:
                skipped += 1
                print(f"  [{i+1}/{len(files_report)}] Skipped: {rel_path} (Error: {e})")
        
        print(f"Indexing complete. {indexed} files indexed, {skipped} files skipped.")

    def search_codebase(self, query: str, n_results: int = 5) -> list[dict]:
        """Perform semantic search on the indexed codebase."""
        db = self.get_chroma_db()
        results = db.similarity_search(query, k=n_results)
        
        search_hits = []
        for doc in results:
            search_hits.append({
                "content": doc.page_content,
                "file_path": doc.metadata.get("file_path"),
                "language": doc.metadata.get("language"),
                "start_line": doc.metadata.get("start_line"),
                "end_line": doc.metadata.get("end_line")
            })
        return search_hits
