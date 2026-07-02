"use client";

import React, { useState, useEffect, useRef } from 'react';
import { 
  FolderGit2, 
  Terminal, 
  Database, 
  Layers, 
  Send, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  Code, 
  Search, 
  HelpCircle,
  FileCode2,
  Network,
  RefreshCw,
  ShieldAlert,
  FileSearch,
  MessageSquare
} from 'lucide-react';
import ReactFlow, { Background, Controls, Edge, Node, Position } from 'reactflow';
import 'reactflow/dist/style.css';

// Type definitions
interface FileInfo {
  path: string;
  lines: number;
  language: string;
}

interface ApiEndpoint {
  method: string;
  path: string;
  handler: string;
  file: string;
  line: number;
}

interface DbModel {
  name: string;
  type: string;
  file: string;
  line: number;
}

interface Summary {
  total_files: number;
  total_lines: number;
  languages: Record<string, number>;
}

interface IngestionReport {
  summary: Summary;
  apis: ApiEndpoint[];
  db_models: DbModel[];
  files: FileInfo[];
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface RepositoryItem {
  id: string;
  name: string;
  local_path: string;
  github_url: string | null;
  status: string;
  created_at: string;
}

export default function Home() {
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  // Config & Ingestion State
  const [ingestMethod, setIngestMethod] = useState<'local' | 'github'>('local');
  const [repoPath, setRepoPath] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<IngestionReport | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'apis' | 'db' | 'map' | 'review' | 'security'>('overview');
  const [codeMapMode, setCodeMapMode] = useState<'api_db' | 'dependencies'>('api_db');
  
  // Persistence state
  const [savedRepos, setSavedRepos] = useState<RepositoryItem[]>([]);
  
  // Agent workers report state
  const [reviewReport, setReviewReport] = useState<string | null>(null);
  const [loadingReview, setLoadingReview] = useState(false);
  const [securityReport, setSecurityReport] = useState<string | null>(null);
  const [loadingSecurity, setLoadingSecurity] = useState(false);

  // Chat state
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Fetch list of already ingested repositories on mount
  useEffect(() => {
    fetchSavedRepositories();
  }, []);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, chatLoading]);

  const fetchSavedRepositories = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/repositories`);
      const data = await response.json();
      if (response.ok && data.success) {
        setSavedRepos(data.repositories);
      }
    } catch (err) {
      console.error("Failed to fetch saved repositories", err);
    }
  };

  // Load a repository session directly without re-ingesting
  const handleLoadRepository = async (repo: RepositoryItem) => {
    setLoading(true);
    setError(null);
    setReport(null);
    setReviewReport(null);
    setSecurityReport(null);
    setChatHistory([]);
    setRepoPath(repo.local_path);
    if (repo.github_url) setGithubUrl(repo.github_url);

    try {
      const response = await fetch(`${API_BASE}/api/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_path: repo.local_path }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to load repository');
      }

      setReport(data);
      setChatHistory([
        {
          role: 'assistant',
          content: `Hi! I have successfully loaded the repository \`${repo.name}\` from \`${repo.local_path}\`.\n\nHere is its metadata overview:\n- **${data.summary.total_files}** files\n- **${data.apis.length}** API endpoints\n- **${data.db_models.length}** Database tables/models\n\nHow would you like to proceed? You can chat with me, or head over to the **Code Review** or **Security Audit** tabs above!`
        }
      ]);
    } catch (err: any) {
      setError(err.message || 'An error occurred loading the repository.');
    } finally {
      setLoading(false);
    }
  };

  // Handle repository ingestion
  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload: { repo_path?: string; github_url?: string } = {};
    
    if (ingestMethod === 'local') {
      const trimmedPath = repoPath.trim();
      if (!trimmedPath) return;
      payload.repo_path = trimmedPath;
    } else {
      const trimmedUrl = githubUrl.trim();
      if (!trimmedUrl) return;
      payload.github_url = trimmedUrl;
    }

    setLoading(true);
    setError(null);
    setReport(null);
    setReviewReport(null);
    setSecurityReport(null);
    setChatHistory([]);

    try {
      const response = await fetch(`${API_BASE}/api/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to ingest repository');
      }

      setReport(data);
      setRepoPath(data.repo_path || repoPath);
      setChatHistory([
        {
          role: 'assistant',
          content: `Hi! I have successfully ingested the repository \`${data.name}\`.\n\nHere is what I found:\n- **${data.summary.total_files}** files\n- **${data.apis.length}** API endpoints\n- **${data.db_models.length}** Database tables/models\n\nHow can I help you understand this codebase? Ask me anything (e.g., *How does authentication work?* or *Where are the APIs defined?*).`
        }
      ]);
      fetchSavedRepositories(); // Refresh historical dropdown list
    } catch (err: any) {
      setError(err.message || 'An error occurred during ingestion.');
    } finally {
      setLoading(false);
    }
  };

  // Handle Code Quality Review
  const triggerCodeReview = async () => {
    if (reviewReport || loadingReview || !report) return;
    setLoadingReview(true);
    try {
      const response = await fetch(`${API_BASE}/api/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_path: repoPath }),
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setReviewReport(data.report);
      } else {
        setReviewReport("### Error\nFailed to compile Code Review report.");
      }
    } catch (err: any) {
      setReviewReport(`### Error\nFailed to run Code Review Agent: ${err.message}`);
    } finally {
      setLoadingReview(false);
    }
  };

  // Handle Security Vulnerability Scanning
  const triggerSecurityAudit = async () => {
    if (securityReport || loadingSecurity || !report) return;
    setLoadingSecurity(true);
    try {
      const response = await fetch(`${API_BASE}/api/security`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_path: repoPath }),
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setSecurityReport(data.report);
      } else {
        setSecurityReport("### Error\nFailed to compile Security Audit report.");
      }
    } catch (err: any) {
      setSecurityReport(`### Error\nFailed to run Security Agent: ${err.message}`);
    } finally {
      setLoadingSecurity(false);
    }
  };

  // Trigger reports automatically on tab clicks
  useEffect(() => {
    if (activeTab === 'review') {
      triggerCodeReview();
    } else if (activeTab === 'security') {
      triggerSecurityAudit();
    }
  }, [activeTab]);

  // Handle chat messaging
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const message = chatInput.trim();
    if (!message || chatLoading || !report) return;

    const userMessage: ChatMessage = { role: 'user', content: message };
    setChatHistory(prev => [...prev, userMessage]);
    setChatInput('');
    setChatLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_path: repoPath,
          message: message,
          history: chatHistory.slice(-10)
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to get response');
      }

      setChatHistory(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (err: any) {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `❌ **Error:** ${err.message || 'Could not reach the AI agent.'}` 
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleQuickPrompt = (promptText: string) => {
    setChatInput(promptText);
  };

  const getFlowElements = () => {
    if (!report) return { nodes: [], edges: [] };

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    if (codeMapMode === 'api_db') {
      const apis = report.apis.slice(0, 8);
      const dbModels = report.db_models.slice(0, 8);

      apis.forEach((api, index) => {
        const id = `api-${index}`;
        nodes.push({
          id,
          data: { 
            label: (
              <div className="p-2 border border-purple-500 rounded bg-slate-900 text-left shadow-lg">
                <div className="flex gap-1.5 items-center mb-1">
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded text-white ${
                    api.method === 'GET' ? 'bg-blue-600' :
                    api.method === 'POST' ? 'bg-emerald-600' :
                    api.method === 'DELETE' ? 'bg-red-600' : 'bg-amber-600'
                  }`}>
                    {api.method}
                  </span>
                  <span className="text-xs font-mono text-purple-300 font-bold truncate max-w-[150px]" title={api.path}>
                    {api.path}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 truncate max-w-[170px]" title={api.file}>
                  {api.handler}() in {api.file.split('/').pop()}
                </div>
              </div>
            ) 
          },
          position: { x: 50, y: index * 110 + 20 },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          style: { background: 'none', border: 'none', width: 200 }
        });
      });

      dbModels.forEach((model, index) => {
        const id = `db-${index}`;
        nodes.push({
          id,
          data: { 
            label: (
              <div className="p-2 border border-emerald-500 rounded bg-slate-900 text-left shadow-lg">
                <div className="flex gap-1.5 items-center mb-1">
                  <Database size={12} className="text-emerald-400" />
                  <span className="text-xs font-mono text-emerald-300 font-bold">
                    {model.name}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400">
                  {model.type}
                </div>
              </div>
            ) 
          },
          position: { x: 450, y: index * 110 + 50 },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          style: { background: 'none', border: 'none', width: 180 }
        });
      });

      apis.forEach((api, apiIdx) => {
        dbModels.forEach((model, dbIdx) => {
          const apiLower = api.path.toLowerCase() + ' ' + api.handler.toLowerCase();
          const modelLower = model.name.toLowerCase();
          const modelBase = modelLower.endsWith('s') ? modelLower.slice(0, -1) : modelLower;
          
          if (apiLower.includes(modelBase) || apiLower.includes(modelLower)) {
            edges.push({
              id: `edge-${apiIdx}-${dbIdx}`,
              source: `api-${apiIdx}`,
              target: `db-${dbIdx}`,
              animated: true,
              style: { stroke: '#a855f7', strokeWidth: 2 },
            });
          }
        });
      });
    } else {
      // Render file dependencies graph (AST)
      const sourceFiles = report.files.filter(f => 
        ['py', 'js', 'jsx', 'ts', 'tsx'].includes(f.language)
      );

      // Simple grid positioning (e.g. 3 columns)
      const cols = 3;
      sourceFiles.forEach((file, index) => {
        const row = Math.floor(index / cols);
        const col = index % cols;
        nodes.push({
          id: file.path,
          data: {
            label: (
              <div className="p-2 border border-blue-500 rounded bg-slate-900 text-left shadow-lg">
                <div className="flex gap-1.5 items-center mb-1">
                  <FileCode2 size={12} className="text-blue-400" />
                  <span className="text-xs font-mono text-blue-300 font-bold truncate max-w-[130px]" title={file.path}>
                    {file.path.split('/').pop()}
                  </span>
                </div>
                <div className="text-[9px] text-slate-500 truncate max-w-[150px]" title={file.path}>
                  {file.path}
                </div>
              </div>
            )
          },
          position: { x: col * 240 + 30, y: row * 110 + 30 },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          style: { background: 'none', border: 'none', width: 180 }
        });

        // Add directed import edges
        if (file.imports) {
          file.imports.forEach((impPath: string) => {
            // Only draw edges if target file is also in sourceFiles to avoid mapping errors
            if (sourceFiles.some(f => f.path === impPath)) {
              edges.push({
                id: `edge-${file.path}-${impPath}`,
                source: file.path,
                target: impPath,
                animated: true,
                style: { stroke: '#3b82f6', strokeWidth: 1.5 }
              });
            }
          });
        }
      });
    }

    return { nodes, edges };
  };

  const { nodes, edges } = getFlowElements();

  const renderMarkdown = (text: string) => {
    return text.split('\n\n').map((paragraph, pIdx) => {
      if (paragraph.startsWith('```')) {
        const lines = paragraph.split('\n');
        const code = lines.slice(1, -1).join('\n');
        return (
          <pre key={pIdx} className="bg-slate-950 border border-slate-800 rounded p-2.5 font-mono text-[10px] text-slate-300 overflow-x-auto my-2">
            <code>{code}</code>
          </pre>
        );
      }
      return <p key={pIdx} className="mb-2">{paragraph}</p>;
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-purple-500/30 selection:text-purple-200">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Layers size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-purple-400 via-indigo-400 to-emerald-400 bg-clip-text text-transparent">
              RepoInsight
            </h1>
            <p className="text-[10px] text-slate-400">Multi-Agent Codebase Auditing Platform</p>
          </div>
        </div>

        {/* Saved Session Selection Dropdown */}
        <div className="flex items-center gap-3">
          {savedRepos.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-slate-500 uppercase font-bold">Session history:</span>
              <select 
                onChange={(e) => {
                  const selected = savedRepos.find(r => r.id === e.target.value);
                  if (selected) handleLoadRepository(selected);
                }}
                defaultValue=""
                className="bg-slate-900 border border-slate-700/60 rounded px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
              >
                <option value="" disabled>Load Saved Repository...</option>
                {savedRepos.map(repo => (
                  <option key={repo.id} value={repo.id}>{repo.name} ({repo.local_path})</option>
                ))}
              </select>
            </div>
          )}

          {report && (
            <div className="flex items-center gap-4 text-xs bg-slate-800/50 px-3 py-1.5 rounded-full border border-slate-700/50">
              <span className="flex items-center gap-1 text-slate-300">
                <FolderGit2 size={12} className="text-purple-400" />
                <span className="truncate max-w-[200px]" title={repoPath}>{repoPath.split('/').pop()}</span>
              </span>
              <span className="h-3 w-px bg-slate-700"></span>
              <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                <CheckCircle2 size={12} />
                Indexed
              </span>
            </div>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex overflow-hidden">
        
        {/* Welcome / Ingestion Screen */}
        {!report ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 max-w-4xl mx-auto text-center">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-emerald-500 flex items-center justify-center shadow-xl shadow-purple-500/10 mb-6">
              <Layers size={36} className="text-white" />
            </div>
            
            <h2 className="text-3xl font-extrabold tracking-tight mb-3 sm:text-4xl bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              Advanced Multi-Agent Codebase Scan
            </h2>
            
            <p className="text-base text-slate-400 mb-8 max-w-xl mx-auto">
              Scan repositories instantly for code quality smells, security vulnerabilities, or ask Q&A questions guided by specialized local agent networks.
            </p>

            <div className="w-full max-w-lg bg-slate-900/50 p-6 rounded-xl border border-slate-800 shadow-2xl backdrop-blur-md">
              
              {/* Ingestion Type Selectors */}
              <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800/80 mb-5">
                <button
                  type="button"
                  onClick={() => setIngestMethod('local')}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold rounded-md transition cursor-pointer ${
                    ingestMethod === 'local' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FolderGit2 size={14} />
                  Local Directory Path
                </button>
                <button
                  type="button"
                  onClick={() => setIngestMethod('github')}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold rounded-md transition cursor-pointer ${
                    ingestMethod === 'github' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FolderGit2 size={14} />
                  Clone GitHub URL
                </button>
              </div>

              <form onSubmit={handleIngest} className="space-y-4 text-left">
                {ingestMethod === 'local' ? (
                  <div className="flex flex-col gap-2">
                    <label className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                      <FolderGit2 size={13} className="text-purple-400" />
                      Absolute Local Repository Path
                    </label>
                    <input
                      type="text"
                      value={repoPath}
                      onChange={(e) => setRepoPath(e.target.value)}
                      placeholder="/Users/username/projects/my-cool-repo"
                      className="w-full bg-slate-950 border border-slate-700/60 rounded-lg px-4 py-3 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500 font-mono text-slate-200"
                      disabled={loading}
                      required
                    />
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <label className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                      <FolderGit2 size={13} className="text-purple-400" />
                      Public GitHub Repository URL
                    </label>
                    <input
                      type="url"
                      value={githubUrl}
                      onChange={(e) => setGithubUrl(e.target.value)}
                      placeholder="https://github.com/username/my-cool-repo"
                      className="w-full bg-slate-950 border border-slate-700/60 rounded-lg px-4 py-3 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500 font-mono text-slate-200"
                      disabled={loading}
                      required
                    />
                  </div>
                )}
                
                {error && (
                  <div className="flex gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 items-start">
                    <AlertCircle size={16} className="shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 active:scale-[0.98] transition text-white text-xs font-semibold py-3 rounded-lg shadow-lg flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:pointer-events-none"
                >
                  {loading ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      {ingestMethod === 'github' ? 'Cloning & Indexing...' : 'Indexing Codebase...'}
                    </>
                  ) : (
                    <>
                      <Terminal size={14} />
                      Ingest & Analyze Codebase
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        ) : (
          
          /* Ingested Dashboard Screen */
          <div className="flex-1 flex overflow-hidden">
            
            {/* Left Panel: Dashboard Metrics & Overview */}
            <div className="w-1/2 flex flex-col border-r border-slate-800 bg-slate-900/10">
              
              {/* Tab Selector */}
              <div className="border-b border-slate-800 bg-slate-900/30 p-2 flex gap-1 overflow-x-auto">
                <button
                  onClick={() => setActiveTab('overview')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition cursor-pointer shrink-0 ${
                    activeTab === 'overview' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Layers size={13} />
                  Overview
                </button>
                <button
                  onClick={() => setActiveTab('apis')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition cursor-pointer shrink-0 ${
                    activeTab === 'apis' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Terminal size={13} />
                  APIs ({report.apis.length})
                </button>
                <button
                  onClick={() => setActiveTab('db')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition cursor-pointer shrink-0 ${
                    activeTab === 'db' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Database size={13} />
                  DB Schema ({report.db_models.length})
                </button>
                <button
                  onClick={() => setActiveTab('map')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition cursor-pointer shrink-0 ${
                    activeTab === 'map' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Network size={13} />
                  Code Map
                </button>
                <button
                  onClick={() => setActiveTab('review')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition cursor-pointer shrink-0 ${
                    activeTab === 'review' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <FileSearch size={13} className="text-amber-400" />
                  Code Review
                </button>
                <button
                  onClick={() => setActiveTab('security')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition cursor-pointer shrink-0 ${
                    activeTab === 'security' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <ShieldAlert size={13} className="text-red-400" />
                  Security Audit
                </button>
              </div>

              {/* Tab Contents */}
              <div className="flex-1 overflow-y-auto p-6">
                
                {/* 1. Overview Tab */}
                {activeTab === 'overview' && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">
                          Total Files
                        </span>
                        <span className="text-xl font-bold text-slate-100">{report.summary.total_files}</span>
                      </div>
                      <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">
                          Lines of Code
                        </span>
                        <span className="text-xl font-bold text-slate-100">
                          {report.summary.total_lines.toLocaleString()}
                        </span>
                      </div>
                      <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">
                          Primary Language
                        </span>
                        <span className="text-xl font-bold text-slate-100 capitalize">
                          {Object.keys(report.summary.languages).sort((a, b) => 
                            report.summary.languages[b] - report.summary.languages[a]
                          )[0] || 'Unknown'}
                        </span>
                      </div>
                    </div>

                    <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                      <h3 className="text-xs font-bold text-slate-300 mb-3 uppercase tracking-wider">Languages</h3>
                      <div className="space-y-2">
                        {Object.entries(report.summary.languages).map(([lang, count]) => {
                          const percentage = Math.round((count / report.summary.total_files) * 100);
                          return (
                            <div key={lang} className="text-xs">
                              <div className="flex justify-between text-slate-400 mb-1">
                                <span className="font-semibold capitalize">{lang} ({count} files)</span>
                                <span>{percentage}%</span>
                              </div>
                              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                                <div className="bg-purple-500 h-full rounded-full" style={{ width: `${percentage}%` }}></div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="bg-slate-900/40 rounded-xl border border-slate-800 overflow-hidden">
                      <div className="p-3.5 bg-slate-900/60 border-b border-slate-800 flex justify-between items-center">
                        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                          <FileCode2 size={13} className="text-purple-400" />
                          Crawled File Repository
                        </h3>
                        <span className="text-[10px] text-slate-500">{report.summary.total_files} files</span>
                      </div>
                      <div className="divide-y divide-slate-800 max-h-72 overflow-y-auto font-mono text-xs">
                        {report.files.map((file, i) => (
                          <div key={i} className="p-2.5 flex justify-between items-center hover:bg-slate-800/20 transition">
                            <span className="text-slate-300 truncate max-w-[340px]">{file.path}</span>
                            <span className="bg-slate-850 px-2 py-0.5 rounded text-[9px] text-slate-400 font-semibold uppercase">{file.language}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. API Endpoints Tab */}
                {activeTab === 'apis' && (
                  <div className="space-y-4">
                    {report.apis.length === 0 ? (
                      <div className="text-center py-12 text-slate-500 text-xs">
                        <Terminal size={32} className="mx-auto mb-2 text-slate-600" />
                        No API endpoints detected in this repository.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {report.apis.map((api, i) => (
                          <div key={i} className="bg-slate-900/50 p-4 rounded-xl border border-slate-800">
                            <div className="flex justify-between items-start gap-2 mb-2">
                              <div className="flex gap-2 items-center">
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded text-white ${
                                  api.method === 'GET' ? 'bg-blue-600' :
                                  api.method === 'POST' ? 'bg-emerald-600' :
                                  api.method === 'DELETE' ? 'bg-red-600' : 'bg-amber-600'
                                }`}>
                                  {api.method}
                                </span>
                                <span className="font-mono text-xs text-purple-300 font-bold">{api.path}</span>
                              </div>
                              <span className="text-[10px] font-mono text-slate-500">{api.handler}()</span>
                            </div>
                            <div className="text-[10px] text-slate-400 flex justify-between border-t border-slate-800/40 pt-2 mt-2 font-mono">
                              <span>{api.file}</span>
                              <span className="text-slate-500">Line {api.line}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 3. Database Schema Tab */}
                {activeTab === 'db' && (
                  <div className="space-y-4">
                    {report.db_models.length === 0 ? (
                      <div className="text-center py-12 text-slate-500 text-xs">
                        <Database size={32} className="mx-auto mb-2 text-slate-600" />
                        No Database models detected in this repository.
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 gap-4">
                        {report.db_models.map((model, i) => (
                          <div key={i} className="bg-slate-900/50 p-4 rounded-xl border border-slate-800">
                            <div className="flex gap-2 items-center mb-2">
                              <Database size={13} className="text-emerald-400" />
                              <span className="font-mono text-xs text-emerald-300 font-bold">{model.name}</span>
                            </div>
                            <div className="text-[10px] text-slate-500 border-t border-slate-800/40 pt-2 mt-2 space-y-1 font-mono">
                              <div>Type: <span className="text-slate-350">{model.type}</span></div>
                              <div className="truncate">File: <span className="text-slate-400">{model.file}</span></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 4. Code Map Tab */}
                {activeTab === 'map' && (
                  <div className="space-y-4 flex flex-col h-[520px]">
                    <div className="flex justify-between items-center bg-slate-900/30 p-2.5 rounded-xl border border-slate-800 shrink-0">
                      <span className="text-[11px] font-bold text-slate-350 uppercase tracking-wider flex items-center gap-1.5">
                        <Network size={13} className="text-purple-400" />
                        Interactive Visual Maps
                      </span>
                      <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800/80">
                        <button
                          type="button"
                          onClick={() => setCodeMapMode('api_db')}
                          className={`px-3 py-1 text-[10px] font-bold rounded-md transition cursor-pointer ${
                            codeMapMode === 'api_db' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-205'
                          }`}
                        >
                          API to DB Map
                        </button>
                        <button
                          type="button"
                          onClick={() => setCodeMapMode('dependencies')}
                          className={`px-3 py-1 text-[10px] font-bold rounded-md transition cursor-pointer ${
                            codeMapMode === 'dependencies' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-205'
                          }`}
                        >
                          File Dependencies (AST)
                        </button>
                      </div>
                    </div>
                    
                    <div className="flex-1 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden relative">
                      {nodes.length === 0 ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 text-xs">
                          <Network size={32} className="mb-2 text-slate-600" />
                          No connected map detected.
                        </div>
                      ) : (
                        <ReactFlow nodes={nodes} edges={edges} fitView>
                          <Background color="#334155" gap={16} />
                          <Controls />
                        </ReactFlow>
                      )}
                    </div>
                  </div>
                )}

                {/* 5. Code Review Tab (New Agent) */}
                {activeTab === 'review' && (
                  <div className="space-y-4 font-sans text-xs leading-relaxed animate-fadeIn">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <h3 className="text-sm font-bold text-amber-400 flex items-center gap-1.5">
                        <FileSearch size={16} />
                        Code Quality Review Report
                      </h3>
                      <button 
                        onClick={() => { setReviewReport(null); triggerCodeReview(); }}
                        disabled={loadingReview}
                        className="text-[10px] text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 rounded px-2.5 py-1 flex items-center gap-1 cursor-pointer"
                      >
                        <RefreshCw size={10} className={loadingReview ? "animate-spin" : ""} />
                        Re-Audit
                      </button>
                    </div>

                    {loadingReview ? (
                      <div className="flex flex-col items-center justify-center py-20 text-slate-450 gap-3">
                        <Loader2 size={32} className="animate-spin text-amber-400" />
                        <span>Code Review Agent is scanning code structures & identifying refactoring improvements...</span>
                      </div>
                    ) : (
                      <div className="bg-slate-900/30 p-5 rounded-xl border border-slate-800 text-slate-200">
                        {reviewReport ? renderMarkdown(reviewReport) : "No review report generated."}
                      </div>
                    )}
                  </div>
                )}

                {/* 6. Security Audit Tab (New Agent) */}
                {activeTab === 'security' && (
                  <div className="space-y-4 font-sans text-xs leading-relaxed animate-fadeIn">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <h3 className="text-sm font-bold text-red-400 flex items-center gap-1.5">
                        <ShieldAlert size={16} />
                        Security Vulnerability Audit
                      </h3>
                      <button 
                        onClick={() => { setSecurityReport(null); triggerSecurityAudit(); }}
                        disabled={loadingSecurity}
                        className="text-[10px] text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 rounded px-2.5 py-1 flex items-center gap-1 cursor-pointer"
                      >
                        <RefreshCw size={10} className={loadingSecurity ? "animate-spin" : ""} />
                        Re-Scan
                      </button>
                    </div>

                    {loadingSecurity ? (
                      <div className="flex flex-col items-center justify-center py-20 text-slate-450 gap-3">
                        <Loader2 size={32} className="animate-spin text-red-400" />
                        <span>Security Agent is checking configuration files & codebase for hardcoded keys and unsafe endpoints...</span>
                      </div>
                    ) : (
                      <div className="bg-slate-900/30 p-5 rounded-xl border border-slate-800 text-slate-200">
                        {securityReport ? renderMarkdown(securityReport) : "No security audit report compiled."}
                      </div>
                    )}
                  </div>
                )}

              </div>
            </div>

            {/* Right Panel: AI Q&A Assistant Chat */}
            <div className="w-1/2 flex flex-col bg-slate-950">
              
              <div className="border-b border-slate-800 bg-slate-900/30 px-5 py-3.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-purple-500 animate-pulse"></div>
                  <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                    <MessageSquare size={13} className="text-purple-400" />
                    AI Q&A Orchestrator
                  </h3>
                </div>
                <button 
                  onClick={() => setChatHistory([
                    {
                      role: 'assistant',
                      content: `Session refreshed. How can I help you explore this codebase?`
                    }
                  ])}
                  className="text-[10px] text-slate-400 hover:text-slate-200 bg-slate-800/40 hover:bg-slate-800 px-2 py-1 rounded transition cursor-pointer"
                >
                  Clear Chat
                </button>
              </div>

              {/* Messages Body */}
              <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
                {chatHistory.map((msg, index) => (
                  <div key={index} className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}>
                    <div className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 ${
                      msg.role === 'user' ? 'bg-purple-600 text-white' : 'bg-slate-800 text-slate-300 border border-slate-700/60'
                    }`}>
                      {msg.role === 'user' ? <HelpCircle size={14} /> : <Layers size={14} className="text-purple-400" />}
                    </div>
                    <div className={`rounded-xl px-4 py-3 leading-relaxed shadow-sm ${
                      msg.role === 'user' ? 'bg-purple-600/90 text-white rounded-tr-none' : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none'
                    }`}>
                      <div className="space-y-2 whitespace-pre-wrap">
                        {renderMarkdown(msg.content)}
                      </div>
                    </div>
                  </div>
                ))}
                
                {chatLoading && (
                  <div className="flex gap-3 mr-auto items-center">
                    <div className="h-7 w-7 rounded-full bg-slate-800 text-slate-300 border border-slate-700/60 flex items-center justify-center shrink-0">
                      <Loader2 size={14} className="animate-spin text-purple-400" />
                    </div>
                    <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 rounded-tl-none text-[11px] text-slate-450 font-medium">
                      Orchestrator routing to worker agent...
                    </div>
                  </div>
                )}
                <div ref={chatEndRef}></div>
              </div>

              {/* Suggestions */}
              {chatHistory.length <= 1 && (
                <div className="px-5 py-2 border-t border-slate-800 bg-slate-900/10 space-y-1.5">
                  <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Ask Specialized Workers</div>
                  <div className="flex flex-wrap gap-1.5">
                    <button 
                      onClick={() => handleQuickPrompt("How does authentication work in this repository?")}
                      className="text-[10px] text-slate-350 hover:text-slate-100 bg-slate-900 hover:bg-slate-850 border border-slate-800 px-2.5 py-1.5 rounded-lg transition text-left cursor-pointer"
                    >
                      Audit Authentications (RAG/Security)
                    </button>
                    <button 
                      onClick={() => handleQuickPrompt("Do a style and performance review of agents.py")}
                      className="text-[10px] text-slate-355 hover:text-slate-100 bg-slate-900 hover:bg-slate-850 border border-slate-800 px-2.5 py-1.5 rounded-lg transition text-left cursor-pointer"
                    >
                      Review agents.py code smells (Review)
                    </button>
                    <button 
                      onClick={() => handleQuickPrompt("Write docstring and structure overview for database/models.py")}
                      className="text-[10px] text-slate-355 hover:text-slate-100 bg-slate-900 hover:bg-slate-850 border border-slate-800 px-2.5 py-1.5 rounded-lg transition text-left cursor-pointer"
                    >
                      Generate model docs (Doc)
                    </button>
                  </div>
                </div>
              )}

              {/* Chat Input form */}
              <form onSubmit={handleSendMessage} className="border-t border-slate-800 bg-slate-900/30 p-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask Q&A, request code reviews, or generate documentation..."
                    className="flex-1 bg-slate-950 border border-slate-700/60 rounded-lg px-4 py-2.5 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500 text-slate-200"
                    disabled={chatLoading}
                  />
                  <button
                    type="submit"
                    disabled={chatLoading || !chatInput.trim()}
                    className="bg-purple-600 hover:bg-purple-500 active:scale-95 transition text-white px-4 py-2.5 rounded-lg flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:pointer-events-none"
                  >
                    <Send size={14} />
                  </button>
                </div>
              </form>

            </div>

          </div>
        )}

      </main>
    </div>
  );
}
