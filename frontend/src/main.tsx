import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8080';

type View = 'documents' | 'chunks' | 'ask' | 'traces' | 'evaluations';

type DocumentRecord = {
  id: string;
  filename: string;
  status: string;
  page_count: number;
  chunk_count: number;
  created_at: string;
};

type ChunkRecord = {
  id: string;
  document_id: string;
  source: string;
  source_type: string;
  title: string;
  page: number;
  chunk_index: number;
  text: string;
  token_estimate: number;
  enabled: boolean;
  tags: string[];
};

type RetrievalResult = {
  id: string;
  title: string;
  text: string;
  score: number;
  source_type: string;
  source?: string;
  page?: number;
  chunk_index?: number;
};

type AskResponse = {
  question: string;
  answer: string;
  faithfulness?: { label: string; score: number; explanation: string; context_doc_ids: string[] };
  document_relevance?: { label: string; score: number; explanation: string; context_doc_ids: string[] };
  failure_mode?: string;
};

type ImprovementCase = {
  case_id: string;
  question: string;
  bad_answer: string;
  faithfulness_label: string;
  faithfulness_score: number;
  failure_mode?: string;
  failure_report: string;
  suggested_fix: string;
};

type TraceSummary = {
  session_id: string;
  timestamp: string;
  question: string;
  answer: string;
  input?: { question: string };
  output?: {
    answer: string;
    faithfulness?: AskResponse['faithfulness'];
    document_relevance?: AskResponse['document_relevance'];
    failure_mode?: string;
  };
  retrieved_documents?: RetrievalResult[];
  faithfulness?: AskResponse['faithfulness'];
  document_relevance?: AskResponse['document_relevance'];
  failure_mode?: string;
  event_count: number;
};

function App() {
  const [view, setView] = useState<View>('documents');
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>('');
  const [chunks, setChunks] = useState<ChunkRecord[]>([]);
  const [selectedChunk, setSelectedChunk] = useState<ChunkRecord | null>(null);
  const [status, setStatus] = useState('Ready');
  const [query, setQuery] = useState('Que agrega el sprint 1?');
  const [searchResults, setSearchResults] = useState<RetrievalResult[]>([]);
  const [question, setQuestion] = useState('Que agrega el sprint 1 y que debe hacer si no hay contexto?');
  const [askResponse, setAskResponse] = useState<AskResponse | null>(null);
  const [cases, setCases] = useState<ImprovementCase[]>([]);
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<TraceSummary | null>(null);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId),
    [documents, selectedDocumentId],
  );

  useEffect(() => {
    refreshDocuments();
    refreshCases();
    refreshTraces();
  }, []);

  useEffect(() => {
    if (selectedDocumentId) {
      refreshChunks(selectedDocumentId);
    }
  }, [selectedDocumentId]);

  async function refreshDocuments() {
    const payload = await fetchJson<{ documents: DocumentRecord[] }>('/documents');
    setDocuments(payload.documents);
    if (!selectedDocumentId && payload.documents.length > 0) {
      setSelectedDocumentId(payload.documents[0].id);
    }
  }

  async function refreshChunks(documentId: string) {
    const payload = await fetchJson<{ chunks: ChunkRecord[] }>(`/documents/${documentId}/chunks`);
    setChunks(payload.chunks);
    setSelectedChunk(payload.chunks[0] ?? null);
  }

  async function refreshCases() {
    const payload = await fetchJson<{ cases: ImprovementCase[] }>('/improvement-cases');
    setCases(payload.cases);
  }

  async function refreshTraces() {
    const payload = await fetchJson<{ traces: TraceSummary[] }>('/introspection/traces?limit=20');
    setTraces(payload.traces);
    setSelectedTrace((current) => current ?? payload.traces[0] ?? null);
  }

  async function uploadPdf(file: File) {
    setStatus('Uploading');
    const body = new FormData();
    body.append('file', file);
    const response = await fetch(`${API_BASE}/documents/pdf`, { method: 'POST', body });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({ detail: response.statusText }));
      setStatus(`Upload failed: ${detail.detail}`);
      return;
    }
    const payload = await response.json();
    setStatus(`Indexed ${payload.chunk_count} chunks`);
    await refreshDocuments();
    setSelectedDocumentId(payload.document.id);
    setView('chunks');
  }

  async function toggleChunk(chunk: ChunkRecord) {
    const payload = await fetchJson<{ chunk: ChunkRecord }>(`/documents/chunks/${chunk.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !chunk.enabled }),
    });
    setChunks((items) => items.map((item) => (item.id === chunk.id ? payload.chunk : item)));
    setSelectedChunk(payload.chunk);
  }

  async function deleteSelectedDocument() {
    if (!selectedDocumentId) return;
    await fetchJson(`/documents/${selectedDocumentId}`, { method: 'DELETE' });
    setSelectedDocumentId('');
    setChunks([]);
    setSelectedChunk(null);
    await refreshDocuments();
  }

  async function runSearch() {
    const payload = await fetchJson<{ documents: RetrievalResult[] }>(
      `/documents/search?query=${encodeURIComponent(query)}&top_k=8`,
    );
    setSearchResults(payload.documents);
  }

  async function ask() {
    setStatus('Asking');
    const payload = await fetchJson<AskResponse>('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    setAskResponse(payload);
    setStatus('Answer ready');
    await refreshCases();
    await refreshTraces();
  }

  async function exportTraces() {
    const payload = await fetchJson<{ exported_at: string; trace_count: number; traces: TraceSummary[] }>(
      '/introspection/traces/export?limit=50',
    );
    downloadJson(`phoenix-reflex-traces-${new Date().toISOString().replace(/[:.]/g, '-')}.json`, payload);
  }

  return (
    <main className="shell">
      <aside className="rail">
        <div className="brand">
          <span>Phoenix Reflex</span>
          <small>PDF Intake</small>
        </div>
        {(['documents', 'chunks', 'ask', 'traces', 'evaluations'] as View[]).map((item) => (
          <button key={item} className={view === item ? 'active' : ''} onClick={() => setView(item)}>
            {labelFor(item)}
          </button>
        ))}
        <div className="railStatus">{status}</div>
      </aside>

      <section className="workspace">
        {view === 'documents' && (
          <DocumentsView
            documents={documents}
            selectedDocumentId={selectedDocumentId}
            onSelect={setSelectedDocumentId}
            onUpload={uploadPdf}
            onDelete={deleteSelectedDocument}
          />
        )}
        {view === 'chunks' && (
          <ChunksView
            document={selectedDocument}
            chunks={chunks}
            selectedChunk={selectedChunk}
            query={query}
            searchResults={searchResults}
            onSelect={setSelectedChunk}
            onToggle={toggleChunk}
            onQuery={setQuery}
            onSearch={runSearch}
          />
        )}
        {view === 'ask' && (
          <AskView question={question} response={askResponse} onQuestion={setQuestion} onAsk={ask} />
        )}
        {view === 'traces' && (
          <TracesView
            traces={traces}
            selectedTrace={selectedTrace}
            onSelect={setSelectedTrace}
            onRefresh={refreshTraces}
            onExport={exportTraces}
          />
        )}
        {view === 'evaluations' && <EvaluationsView cases={cases} onRefresh={refreshCases} />}
      </section>
    </main>
  );
}

function DocumentsView({
  documents,
  selectedDocumentId,
  onSelect,
  onUpload,
  onDelete,
}: {
  documents: DocumentRecord[];
  selectedDocumentId: string;
  onSelect: (id: string) => void;
  onUpload: (file: File) => void;
  onDelete: () => void;
}) {
  return (
    <div className="twoPane">
      <section>
        <header className="sectionHeader">
          <div>
            <h1>Documents</h1>
            <p>Upload local PDFs and decide what enters retrieval.</p>
          </div>
        </header>
        <label className="dropzone">
          <input type="file" accept="application/pdf" onChange={(event) => event.target.files?.[0] && onUpload(event.target.files[0])} />
          <strong>Drop or choose a PDF</strong>
          <span>Text PDFs only. OCR is intentionally out of scope for v1.</span>
        </label>
        <table>
          <thead>
            <tr><th>File</th><th>Status</th><th>Pages</th><th>Chunks</th></tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.id} className={document.id === selectedDocumentId ? 'selected' : ''} onClick={() => onSelect(document.id)}>
                <td>{document.filename}</td>
                <td>{document.status}</td>
                <td>{document.page_count}</td>
                <td>{document.chunk_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <aside className="inspector">
        <h2>Inspector</h2>
        {selectedDocumentId ? (
          <>
            <dl>
              <dt>Document ID</dt><dd>{selectedDocumentId}</dd>
            </dl>
            <button className="danger" onClick={onDelete}>Delete document</button>
          </>
        ) : <p>No document selected.</p>}
      </aside>
    </div>
  );
}

function ChunksView(props: {
  document?: DocumentRecord;
  chunks: ChunkRecord[];
  selectedChunk: ChunkRecord | null;
  query: string;
  searchResults: RetrievalResult[];
  onSelect: (chunk: ChunkRecord) => void;
  onToggle: (chunk: ChunkRecord) => void;
  onQuery: (query: string) => void;
  onSearch: () => void;
}) {
  return (
    <div className="twoPane">
      <section>
        <header className="sectionHeader">
          <div>
            <h1>Chunks</h1>
            <p>{props.document ? props.document.filename : 'Select a document to review chunks.'}</p>
          </div>
          <div className="searchBox">
            <input value={props.query} onChange={(event) => props.onQuery(event.target.value)} />
            <button onClick={props.onSearch}>Test retrieval</button>
          </div>
        </header>
        <table>
          <thead>
            <tr><th>Enabled</th><th>Page</th><th>Chunk</th><th>Preview</th><th>Chars</th></tr>
          </thead>
          <tbody>
            {props.chunks.map((chunk) => (
              <tr key={chunk.id} className={props.selectedChunk?.id === chunk.id ? 'selected' : ''} onClick={() => props.onSelect(chunk)}>
                <td><button onClick={(event) => { event.stopPropagation(); props.onToggle(chunk); }}>{chunk.enabled ? 'On' : 'Off'}</button></td>
                <td>{chunk.page}</td>
                <td>{chunk.chunk_index}</td>
                <td>{chunk.text.slice(0, 120)}</td>
                <td>{chunk.text.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {props.searchResults.length > 0 && (
          <section className="results">
            <h2>Retrieval test</h2>
            {props.searchResults.map((result) => (
              <div key={result.id} className="resultLine">
                <strong>{result.id}</strong><span>{result.score}</span>
              </div>
            ))}
          </section>
        )}
      </section>
      <aside className="inspector">
        <h2>Chunk text</h2>
        {props.selectedChunk ? (
          <>
            <dl>
              <dt>ID</dt><dd>{props.selectedChunk.id}</dd>
              <dt>Citation</dt><dd>pdf:{props.selectedChunk.source} p.{props.selectedChunk.page} c.{props.selectedChunk.chunk_index}</dd>
            </dl>
            <pre>{props.selectedChunk.text}</pre>
          </>
        ) : <p>No chunk selected.</p>}
      </aside>
    </div>
  );
}

function AskView({ question, response, onQuestion, onAsk }: {
  question: string;
  response: AskResponse | null;
  onQuestion: (question: string) => void;
  onAsk: () => void;
}) {
  return (
    <div className="askLayout">
      <section>
        <header className="sectionHeader">
          <div>
            <h1>Ask with sources</h1>
            <p>Run the current RAG and inspect answer quality.</p>
          </div>
        </header>
        <textarea value={question} onChange={(event) => onQuestion(event.target.value)} />
        <button className="primary" onClick={onAsk}>Ask</button>
        {response && (
          <article className="answer">
            <h2>Answer</h2>
            <p>{response.answer}</p>
          </article>
        )}
      </section>
      <aside className="inspector">
        <h2>Evaluations</h2>
        {response ? (
          <>
            <Metric label="Faithfulness" value={`${response.faithfulness?.label ?? '-'} ${response.faithfulness?.score ?? ''}`} />
            <Metric label="Document relevance" value={`${response.document_relevance?.label ?? '-'} ${response.document_relevance?.score ?? ''}`} />
            <Metric label="Failure mode" value={response.failure_mode ?? '-'} />
            <p>{response.faithfulness?.explanation}</p>
          </>
        ) : <p>No answer yet.</p>}
      </aside>
    </div>
  );
}

function EvaluationsView({ cases, onRefresh }: { cases: ImprovementCase[]; onRefresh: () => void }) {
  return (
    <section>
      <header className="sectionHeader">
        <div>
          <h1>Evaluations</h1>
          <p>Regression cases and prompt loop outputs.</p>
        </div>
        <button onClick={onRefresh}>Refresh</button>
      </header>
      <table>
        <thead>
          <tr><th>Case</th><th>Question</th><th>Label</th><th>Failure mode</th><th>Suggested fix</th></tr>
        </thead>
        <tbody>
          {cases.map((item) => (
            <tr key={item.case_id}>
              <td>{item.case_id}</td>
              <td>{item.question}</td>
              <td>{item.faithfulness_label} {item.faithfulness_score}</td>
              <td>{item.failure_mode ?? '-'}</td>
              <td>{item.suggested_fix}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function TracesView({
  traces,
  selectedTrace,
  onSelect,
  onRefresh,
  onExport,
}: {
  traces: TraceSummary[];
  selectedTrace: TraceSummary | null;
  onSelect: (trace: TraceSummary) => void;
  onRefresh: () => void;
  onExport: () => void;
}) {
  return (
    <div className="twoPane">
      <section>
        <header className="sectionHeader">
          <div>
            <h1>Trace IO</h1>
            <p>Captured local inputs, outputs, retrieval context, and evaluator outputs.</p>
          </div>
          <div className="actions">
            <button onClick={onRefresh}>Refresh</button>
            <button onClick={onExport}>Export JSON</button>
          </div>
        </header>
        <table>
          <thead>
            <tr><th>Time</th><th>Session</th><th>Input</th><th>Faithfulness</th><th>Failure</th></tr>
          </thead>
          <tbody>
            {traces.map((trace) => (
              <tr key={trace.session_id} className={selectedTrace?.session_id === trace.session_id ? 'selected' : ''} onClick={() => onSelect(trace)}>
                <td>{formatTime(trace.timestamp)}</td>
                <td>{trace.session_id.slice(0, 18)}...</td>
                <td>{trace.question}</td>
                <td>{trace.faithfulness?.label ?? '-'} {trace.faithfulness?.score ?? ''}</td>
                <td>{trace.failure_mode ?? '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <aside className="inspector">
        <h2>Trace detail</h2>
        {selectedTrace ? (
          <>
            <dl>
              <dt>Session ID</dt><dd>{selectedTrace.session_id}</dd>
              <dt>Timestamp</dt><dd>{selectedTrace.timestamp}</dd>
              <dt>Events</dt><dd>{selectedTrace.event_count}</dd>
            </dl>
            <section className="traceBlock">
              <h3>Input</h3>
              <pre>{selectedTrace.question}</pre>
            </section>
            <section className="traceBlock">
              <h3>Output</h3>
              <pre>{selectedTrace.answer}</pre>
            </section>
            <section className="traceBlock">
              <h3>Retrieved documents</h3>
              {(selectedTrace.retrieved_documents ?? []).map((doc) => (
                <div key={doc.id} className="resultLine">
                  <strong>{doc.id}</strong><span>{doc.score}</span>
                </div>
              ))}
            </section>
            <section className="traceBlock">
              <h3>Evaluations</h3>
              <pre>{JSON.stringify({
                faithfulness: selectedTrace.faithfulness,
                document_relevance: selectedTrace.document_relevance,
                failure_mode: selectedTrace.failure_mode,
              }, null, 2)}</pre>
            </section>
            <button onClick={() => downloadJson(`trace-${selectedTrace.session_id}.json`, selectedTrace)}>Export selected</button>
          </>
        ) : <p>No traces captured yet. Ask a question first.</p>}
      </aside>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function labelFor(view: View) {
  return { documents: 'Documents', chunks: 'Chunks', ask: 'Ask', traces: 'Traces', evaluations: 'Evaluations' }[view];
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(href);
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

createRoot(document.getElementById('root')!).render(<App />);
