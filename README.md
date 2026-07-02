# RepoInsight 🚀

**RepoInsight** is an AI-powered codebase onboarding and Q&A platform designed to help developers instantly understand a new codebase. Instead of spending days browsing through files, mapping out APIs, and tracing database models, RepoInsight extracts the entire structure automatically and answers technical questions in seconds.

This project is built using a **Python (FastAPI) backend** utilizing **LangChain** and **Google Gemini**, combined with a **Next.js (React) + Tailwind CSS frontend**.

---

## Key Features

1. **Static Analysis & AST Parsing**: Automatically crawls files and runs Abstract Syntax Tree (AST) parsing to identify python functions, classes, decorators, routes, and database models.
2. **AI Code Agent (LangChain)**: An intelligent software agent configured with custom tools to do semantic code search, list endpoints, and query schema configurations.
3. **Semantic Embedding Retrieval (RAG)**: Chunks code dynamically by logical syntax blocks (e.g. functions, modules) and indexes them in a local vector database (**ChromaDB**).
4. **Interactive Codebase Dashboard**: Displays summary stats (total files, lines, language distribution) alongside structured tabs for detected REST APIs and ORM schemas.
5. **Visual Architecture Code Map**: An interactive graph showing connections from API routes to the database tables they touch (built using **React Flow**).
6. **Code Q&A Chat Console**: A clean, modern chat interface to ask code-specific questions, complete with markdown rendering and syntax highlighting.

---

## Project Architecture

```
major_p/
├── backend/                   # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py            # FastAPI Entry point
│   │   ├── api/               # API routes (/ingest and /chat)
│   │   ├── services/
│   │   │   ├── parser.py      # Repository AST Crawler & Parser
│   │   │   ├── vector_db.py   # ChromaDB Embeddings Indexer
│   │   │   └── agent.py       # LangChain Agent & Tools binding
│   │   └── core/
│   │       └── config.py      # App Config & Env loading
│   ├── requirements.txt       # Backend Dependencies
│   └── .env                   # Local Environment Config
│
├── frontend/                  # Next.js Frontend
│   ├── src/
│   │   ├── app/               # Next.js App Router (page.tsx, globals.css)
│   │   ├── components/        # Frontend Components
│   │   └── services/          # API Services
│   ├── package.json           # Frontend Dependencies
│   └── tsconfig.json          # TypeScript Configuration
└── README.md                  # Setup & Usage Guide
```

---

## Setup & Installation

### Prerequisites
* Python 3.10 or higher
* Node.js v18 or higher
* Google Gemini API Key (Get one from [Google AI Studio](https://aistudio.google.com/))

### 1. Backend Setup
1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   * Rename `.env` (or create one) and configure your `GEMINI_API_KEY`:
     ```env
     GEMINI_API_KEY=your_google_gemini_api_key_here
     LLM_PROVIDER=ollama
     OLLAMA_MODEL=qwen2.5:3b
     GEMINI_CHAT_MODEL=gemini-2.0-flash
     GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
     EMBEDDING_PROVIDER=local
     CHROMA_DB_PATH=./chroma_db
     PORT=8000
     ```
   * `LLM_PROVIDER=ollama` uses a local Ollama model for personalized answers.
     Make sure Ollama is running and the model is pulled:
     ```bash
     ollama pull qwen2.5:3b
     ```
   * `EMBEDDING_PROVIDER=local` keeps ingestion offline and avoids Gemini
     quota/network failures during indexing. Set it to `gemini` only if your
     Gemini key has working embedding quota.
   * If you see a quota error such as `quota limit 0`, the issue is with the
     Google project/API key quota, not RepoInsight. Create or switch to a
     Gemini API key with available `generateContent` quota, enable billing if
     needed, or set `GEMINI_CHAT_MODEL` to another model that your key can use
     such as `gemini-2.5-flash`, `gemini-flash-latest`, or another model shown
     in Google AI Studio for that key.
5. Start the backend server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   * Access the interactive API docs at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup
1. In a new terminal, navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install the node packages:
   ```bash
   npm install
   ```
3. Run the Next.js development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to: [http://localhost:3000](http://localhost:3000)

---

## Verification & Usage Guide

1. Open the UI at [http://localhost:3000](http://localhost:3000).
2. Enter the **absolute local path** of a repository you want to analyze (you can even type the path of this project: `/Users/.../major_p/backend`).
3. Click **Ingest & Analyze Codebase**. The server will crawl, index, and analyze it.
4. **Browse Dashboard**: Click through the tabs:
   * **Overview**: Check LOC count and file language breakdown.
   * **API Endpoints**: Check endpoints, handler names, and file positions.
   * **DB Schema**: View SQLAlchemy or raw SQL model definitions.
   * **Code Map**: Drag around nodes mapping APIs to DB models.
5. **Chat with AI**: Ask questions in the right panel:
   * *"What does parser.py do?"*
   * *"How does the chat route retrieve history?"*
   * *"Explain where the vector database is initialized."*
