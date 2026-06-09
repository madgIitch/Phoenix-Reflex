import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

type View = 'documents' | 'chunks' | 'ask' | 'traces' | 'evaluations' | 'mcp';

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

type EvalScore = { label: string; score: number; explanation: string; context_doc_ids: string[] };

type AnswerQuality = { label: string; reasons: string[]; explanation: string };

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

type LoopSummary = {
  steps: string[];
  correction: {
    attempted: boolean;
    rounds: number;
    phantom_citations_detected_count: number;
    phantom_citations_corrected_count: number;
    style_correction_applied: boolean;
  };
  eval: {
    faithfulness?: EvalScore;
    document_relevance?: EvalScore;
    answer_quality?: AnswerQuality;
    failure_mode?: string;
  };
  improvement_case: ImprovementCase | null;
};

type AskResponse = {
  question: string;
  answer: string;
  faithfulness?: EvalScore;
  document_relevance?: EvalScore;
  answer_quality?: AnswerQuality;
  failure_mode?: string;
  phantom_citations_detected_count?: number;
  phantom_citations_corrected_count?: number;
  phantom_citations?: string[];
  style_correction_applied?: boolean;
  improvement_case?: ImprovementCase | null;
  loop?: LoopSummary;
  session_id?: string;
  event_count?: number;
  phoenix_mcp_called?: boolean;
  phoenix_mcp_call_count?: number;
  phoenix_mcp_tools?: string[];
  phoenix_mcp_evidence?: PhoenixMcpEvidence[];
};

type PhoenixMcpEvidence = {
  tool: string;
  summary: string;
};

type McpStatus = {
  enabled: boolean;
  configured: boolean;
  importable: boolean;
  demo_ready: boolean;
  phoenix_host: string;
  tool_filter: string[];
  missing: string[];
  model: string;
  tracing_backend: string;
  note: string;
};

type PromptRecord = {
  tag: string;
  version: string;
  prompt: string;
  source: string;
  created_at?: string;
};

type CandidateResponse = {
  candidate: PromptRecord;
  regression_case_count: number;
};

type PromptExperimentResponse = {
  candidate_version: string;
  n_runs: number;
  production_regression_avg: number;
  candidate_regression_avg: number;
  production_good_avg: number;
  candidate_good_avg: number;
  should_promote_to_staging: boolean;
  regression_results: Array<{ case_id?: string; question: string; production_score: number; candidate_score: number }>;
  good_results: Array<{ question: string; production_score: number; candidate_score: number }>;
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
    answer_quality?: AskResponse['answer_quality'];
    failure_mode?: string;
  };
  retrieved_documents?: RetrievalResult[];
  faithfulness?: AskResponse['faithfulness'];
  document_relevance?: AskResponse['document_relevance'];
  answer_quality?: AskResponse['answer_quality'];
  failure_mode?: string;
  event_count: number;
  phantom_citations_detected_count?: number;
  phantom_citations_corrected_count?: number;
  phantom_citations?: string[];
  style_correction_applied?: boolean;
  phoenix_mcp_called?: boolean;
  phoenix_mcp_call_count?: number;
  phoenix_mcp_tools?: string[];
  phoenix_mcp_evidence?: PhoenixMcpEvidence[];
};

function App() {
  const [view, setView] = useState<View>('documents');
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>('');
  const [chunks, setChunks] = useState<ChunkRecord[]>([]);
  const [selectedChunk, setSelectedChunk] = useState<ChunkRecord | null>(null);
  const [status, setStatus] = useState('Ready');
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<RetrievalResult[]>([]);
  const [question, setQuestion] = useState('');
  const [askResponse, setAskResponse] = useState<AskResponse | null>(null);
  const [cases, setCases] = useState<ImprovementCase[]>([]);
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<TraceSummary | null>(null);
  const [mcpStatus, setMcpStatus] = useState<McpStatus | null>(null);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId),
    [documents, selectedDocumentId],
  );

  useEffect(() => {
    refreshDocuments();
    refreshCases();
    refreshTraces();
    refreshMcpStatus();
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

  async function refreshMcpStatus() {
    const payload = await fetchJson<McpStatus>('/observability/mcp');
    setMcpStatus(payload);
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
        {(['documents', 'chunks', 'ask', 'traces', 'evaluations', 'mcp'] as View[]).map((item) => (
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
        {view === 'mcp' && (
          <McpView
            status={mcpStatus}
            lastResponse={askResponse}
            traces={traces}
            onRefresh={async () => {
              await refreshMcpStatus();
              await refreshTraces();
            }}
            onUseDemoQuestion={() => {
              setQuestion('What failed in the latest traces, and what improvement should we make next?');
              setView('ask');
            }}
          />
        )}
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
  const [candidate, setCandidate] = useState<CandidateResponse | null>(null);
  const [experiment, setExperiment] = useState<PromptExperimentResponse | null>(null);
  const [loopStatus, setLoopStatus] = useState('');

  useEffect(() => {
    setCandidate(null);
    setExperiment(null);
    setLoopStatus('');
  }, [response?.session_id]);

  async function generateCandidate() {
    setLoopStatus('Generating candidate');
    const payload = await fetchJson<CandidateResponse>('/prompts/candidate', { method: 'POST' });
    setCandidate(payload);
    setExperiment(null);
    setLoopStatus('Candidate ready');
  }

  async function runExperiment() {
    setLoopStatus('Running experiment');
    const payload = await fetchJson<PromptExperimentResponse>('/experiments/prompt?n_runs=1', { method: 'POST' });
    setExperiment(payload);
    setLoopStatus('Experiment ready');
  }

  const improvementCase = response?.loop?.improvement_case ?? response?.improvement_case ?? null;

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
        {response && (
          <LoopMissionPanel
            response={response}
            improvementCase={improvementCase}
            candidate={candidate}
            experiment={experiment}
            status={loopStatus}
            onGenerateCandidate={generateCandidate}
            onRunExperiment={runExperiment}
          />
        )}
      </section>
      <aside className="inspector">
        <h2>Evaluations</h2>
        {response ? (
          <>
            <Metric label="Faithfulness" value={`${response.faithfulness?.label ?? '-'} ${response.faithfulness?.score ?? ''}`} />
            <Metric label="Document relevance" value={`${response.document_relevance?.label ?? '-'} ${response.document_relevance?.score ?? ''}`} />
            <Metric label="Answer quality" value={response.answer_quality?.label ?? '-'} />
            <Metric label="Failure mode" value={response.failure_mode ?? '-'} />
            <p>{response.faithfulness?.explanation}</p>
            {response.answer_quality?.label === 'suspicious' && <p>{response.answer_quality.explanation}</p>}
            <CorrectionLoopPanel
              detected={response.phantom_citations_detected_count ?? 0}
              corrected={response.phantom_citations_corrected_count ?? 0}
              remaining={response.phantom_citations ?? []}
              styleFixed={response.style_correction_applied ?? false}
              eventCount={response.event_count ?? 0}
            />
            {improvementCase && (
              <ImprovementCasePanel caseItem={improvementCase} compact />
            )}
            <McpEvidencePanel
              called={response.phoenix_mcp_called ?? false}
              callCount={response.phoenix_mcp_call_count ?? 0}
              tools={response.phoenix_mcp_tools ?? []}
              evidence={response.phoenix_mcp_evidence ?? []}
            />
          </>
        ) : <p>No answer yet.</p>}
      </aside>
    </div>
  );
}

function LoopMissionPanel({
  response,
  improvementCase,
  candidate,
  experiment,
  status,
  onGenerateCandidate,
  onRunExperiment,
}: {
  response: AskResponse;
  improvementCase: ImprovementCase | null;
  candidate: CandidateResponse | null;
  experiment: PromptExperimentResponse | null;
  status: string;
  onGenerateCandidate: () => void;
  onRunExperiment: () => void;
}) {
  const loop = response.loop;

  return (
    <section className="loopMission">
      <div className="loopMissionHeader">
        <div>
          <h2>Regression loop</h2>
          <p>Correction, evaluation, regression case, prompt candidate, and experiment stay in one operator flow.</p>
        </div>
        {status && <span className="actionStatus">{status}</span>}
      </div>
      <div className="loopTimeline">
        <LoopStep
          index="1"
          title="Correction"
          state={loop?.correction.attempted ? 'applied' : 'clean'}
          detail={`${loop?.correction.rounds ?? 0} citation rounds, ${loop?.correction.style_correction_applied ? 'style fixed' : 'style clean'}`}
        />
        <LoopStep
          index="2"
          title="Eval"
          state={response.failure_mode ?? 'unknown'}
          detail={`Faithfulness ${response.faithfulness?.score ?? '-'} · relevance ${response.document_relevance?.score ?? '-'}`}
        />
        <LoopStep
          index="3"
          title="Case"
          state={improvementCase ? 'captured' : 'not needed'}
          detail={improvementCase?.case_id ?? 'No regression case from this answer'}
        />
        <LoopStep
          index="4"
          title="Candidate"
          state={candidate ? 'ready' : 'manual action'}
          detail={candidate ? `${candidate.regression_case_count} regression cases used` : 'Generate after a captured case'}
        />
        <LoopStep
          index="5"
          title="Experiment"
          state={experiment ? 'complete' : 'waiting'}
          detail={experiment ? `promote recommendation: ${experiment.should_promote_to_staging ? 'yes' : 'no'}` : 'Run after candidate'}
        />
      </div>

      {improvementCase ? (
        <ImprovementCasePanel caseItem={improvementCase} />
      ) : (
        <div className="loopEmpty">
          <strong>No improvement case captured</strong>
          <span>The answer passed the current failure thresholds, so candidate generation is disabled for this run.</span>
        </div>
      )}

      <div className="loopActions">
        <button className="primary" onClick={onGenerateCandidate} disabled={!improvementCase}>
          Generate Candidate
        </button>
        <button onClick={onRunExperiment} disabled={!candidate}>
          Run Experiment
        </button>
      </div>

      {candidate && (
        <section className="traceBlock">
          <h3>Candidate prompt</h3>
          <Metric label="Version" value={candidate.candidate.version} />
          <Metric label="Regression cases" value={String(candidate.regression_case_count)} />
          <pre>{candidate.candidate.prompt}</pre>
        </section>
      )}

      {experiment && (
        <section className="traceBlock">
          <h3>Experiment decision</h3>
          <Metric label="Candidate version" value={experiment.candidate_version} />
          <Metric label="Should promote to staging" value={experiment.should_promote_to_staging ? 'yes' : 'no'} />
          <Metric label="Regression delta" value={`${experiment.production_regression_avg} -> ${experiment.candidate_regression_avg}`} />
          <Metric label="Good-question guard" value={`${experiment.production_good_avg} -> ${experiment.candidate_good_avg}`} />
          <p>Promotion remains manual; this flow does not call the promote endpoint.</p>
        </section>
      )}
    </section>
  );
}

function LoopStep({ index, title, state, detail }: { index: string; title: string; state: string; detail: string }) {
  return (
    <div className="loopStep">
      <span>{index}</span>
      <strong>{title}</strong>
      <em>{state}</em>
      <small>{detail}</small>
    </div>
  );
}

function ImprovementCasePanel({ caseItem, compact = false }: { caseItem: ImprovementCase; compact?: boolean }) {
  return (
    <div className={compact ? 'casePanel compact' : 'casePanel'}>
      <div className="correctionHeader">
        <span>Improvement case</span>
        <span className="correctionTag failed">{caseItem.failure_mode ?? 'failure'}</span>
      </div>
      <Metric label="Case" value={caseItem.case_id} />
      <Metric label="Faithfulness" value={`${caseItem.faithfulness_label} ${caseItem.faithfulness_score}`} />
      {!compact && (
        <>
          <p>{caseItem.failure_report}</p>
          <pre>{caseItem.suggested_fix}</pre>
        </>
      )}
    </div>
  );
}

function McpView({
  status,
  lastResponse,
  traces,
  onRefresh,
  onUseDemoQuestion,
}: {
  status: McpStatus | null;
  lastResponse: AskResponse | null;
  traces: TraceSummary[];
  onRefresh: () => void;
  onUseDemoQuestion: () => void;
}) {
  const mcpTraces = traces.filter((trace) => trace.phoenix_mcp_called);

  return (
    <div className="twoPane">
      <section>
        <header className="sectionHeader">
          <div>
            <h1>Observability MCP</h1>
            <p>Phoenix MCP readiness and runtime evidence for the Arize demo.</p>
          </div>
          <div className="actions">
            <button onClick={onUseDemoQuestion}>Use demo question</button>
            <button onClick={onRefresh}>Refresh</button>
          </div>
        </header>
        {status ? (
          <div className="statusGrid">
            <StatusTile label="Demo ready" value={status.demo_ready ? 'yes' : 'no'} good={status.demo_ready} />
            <StatusTile label="Enabled" value={status.enabled ? 'yes' : 'no'} good={status.enabled} />
            <StatusTile label="Configured" value={status.configured ? 'yes' : 'no'} good={status.configured} />
            <StatusTile label="Importable" value={status.importable ? 'yes' : 'no'} good={status.importable} />
          </div>
        ) : <p>MCP status has not loaded yet.</p>}
        {status && (
          <section className="traceBlock">
            <h3>Runtime configuration</h3>
            <Metric label="Phoenix host" value={status.phoenix_host || '-'} />
            <Metric label="Tracing backend" value={status.tracing_backend} />
            <Metric label="Model" value={status.model} />
            <Metric label="Missing" value={status.missing.length ? status.missing.join(', ') : '-'} />
            <p>{status.note}</p>
          </section>
        )}
        {status && (
          <section className="traceBlock">
            <h3>Phoenix MCP tools</h3>
            <div className="toolList">
              {status.tool_filter.map((tool) => <code key={tool}>{tool}</code>)}
            </div>
          </section>
        )}
        <section className="traceBlock">
          <h3>Recent MCP traces</h3>
          <table>
            <thead>
              <tr><th>Time</th><th>Session</th><th>Question</th><th>Tools</th></tr>
            </thead>
            <tbody>
              {mcpTraces.map((trace) => (
                <tr key={trace.session_id}>
                  <td>{formatTime(trace.timestamp)}</td>
                  <td>{trace.session_id.slice(0, 18)}...</td>
                  <td>{trace.question}</td>
                  <td>{(trace.phoenix_mcp_tools ?? []).join(', ') || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {mcpTraces.length === 0 && <p>No Phoenix MCP calls captured yet. Use the demo question from this tab, then ask it.</p>}
        </section>
      </section>
      <aside className="inspector">
        <h2>Last /ask MCP evidence</h2>
        {lastResponse ? (
          <McpEvidencePanel
            called={lastResponse.phoenix_mcp_called ?? false}
            callCount={lastResponse.phoenix_mcp_call_count ?? 0}
            tools={lastResponse.phoenix_mcp_tools ?? []}
            evidence={lastResponse.phoenix_mcp_evidence ?? []}
          />
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
  const [copyStatus, setCopyStatus] = useState('');

  async function copySelectedTrace() {
    if (!selectedTrace) return;
    await copyJsonToClipboard(selectedTrace);
    setCopyStatus('Copied');
    window.setTimeout(() => setCopyStatus(''), 1800);
  }

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
            <tr><th>Time</th><th>Session</th><th>Input</th><th>Faithfulness</th><th>Quality</th><th>Failure</th><th>MCP</th><th>Corrections</th></tr>
          </thead>
          <tbody>
            {traces.map((trace) => (
              <tr key={trace.session_id} className={selectedTrace?.session_id === trace.session_id ? 'selected' : ''} onClick={() => onSelect(trace)}>
                <td>{formatTime(trace.timestamp)}</td>
                <td>{trace.session_id.slice(0, 18)}...</td>
                <td>{trace.question}</td>
                <td>{trace.faithfulness?.label ?? '-'} {trace.faithfulness?.score ?? ''}</td>
                <td>{trace.answer_quality?.label ?? '-'}</td>
                <td>{trace.failure_mode ?? '-'}</td>
                <td>{trace.phoenix_mcp_called ? <span className="correctionTag fixed">used</span> : <span className="correctionTag clean">-</span>}</td>
                <td><CorrectionBadge detected={trace.phantom_citations_detected_count ?? 0} corrected={trace.phantom_citations_corrected_count ?? 0} styleFixed={trace.style_correction_applied ?? false} /></td>
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
              <Metric label="Faithfulness" value={`${selectedTrace.faithfulness?.label ?? '-'} ${selectedTrace.faithfulness?.score ?? ''}`} />
              <Metric label="Document relevance" value={`${selectedTrace.document_relevance?.label ?? '-'} ${selectedTrace.document_relevance?.score ?? ''}`} />
              <Metric label="Answer quality" value={selectedTrace.answer_quality?.label ?? '-'} />
              <Metric label="Failure mode" value={selectedTrace.failure_mode ?? '-'} />
            </section>
            <section className="traceBlock">
              <h3>Correction loop</h3>
              <CorrectionLoopPanel
                detected={selectedTrace.phantom_citations_detected_count ?? 0}
                corrected={selectedTrace.phantom_citations_corrected_count ?? 0}
                remaining={selectedTrace.phantom_citations ?? []}
                styleFixed={selectedTrace.style_correction_applied ?? false}
                eventCount={selectedTrace.event_count ?? 0}
              />
            </section>
            <section className="traceBlock">
              <h3>Phoenix MCP</h3>
              <McpEvidencePanel
                called={selectedTrace.phoenix_mcp_called ?? false}
                callCount={selectedTrace.phoenix_mcp_call_count ?? 0}
                tools={selectedTrace.phoenix_mcp_tools ?? []}
                evidence={selectedTrace.phoenix_mcp_evidence ?? []}
              />
            </section>
            <div className="actions">
              <button onClick={copySelectedTrace}>Copy JSON</button>
              <button onClick={() => downloadJson(`trace-${selectedTrace.session_id}.json`, selectedTrace)}>Export selected</button>
              {copyStatus && <span className="actionStatus">{copyStatus}</span>}
            </div>
          </>
        ) : <p>No traces captured yet. Ask a question first.</p>}
      </aside>
    </div>
  );
}

function CorrectionLoopPanel({ detected, corrected, remaining, styleFixed, eventCount }: {
  detected: number;
  corrected: number;
  remaining: string[];
  styleFixed: boolean;
  eventCount: number;
}) {
  const allFixed = detected > 0 && corrected === detected && remaining.length === 0;
  const partialFail = detected > 0 && remaining.length > 0;

  return (
    <div className="correctionPanel">
      <div className="correctionHeader">
        <span>Correction loop</span>
        {detected === 0 && !styleFixed && <span className="correctionTag clean">clean</span>}
        {allFixed && <span className="correctionTag fixed">self-corrected</span>}
        {partialFail && <span className="correctionTag failed">correction failed</span>}
        {styleFixed && <span className="correctionTag fixed">style fixed</span>}
      </div>
      <Metric label="Phantom citations detected" value={String(detected)} />
      <Metric label="Phantom citations corrected" value={String(corrected)} />
      {remaining.length > 0 && (
        <div className="correctionRemaining">
          <span>Remaining</span>
          <code>{remaining.join(', ')}</code>
        </div>
      )}
      <Metric label="Style correction applied" value={styleFixed ? 'yes' : 'no'} />
      <Metric label="Agent turn count" value={String(eventCount)} />
    </div>
  );
}

function McpEvidencePanel({ called, callCount, tools, evidence }: {
  called: boolean;
  callCount: number;
  tools: string[];
  evidence: PhoenixMcpEvidence[];
}) {
  return (
    <div className="correctionPanel">
      <div className="correctionHeader">
        <span>Phoenix MCP</span>
        {called ? <span className="correctionTag fixed">used</span> : <span className="correctionTag clean">not used</span>}
      </div>
      <Metric label="Called" value={called ? 'yes' : 'no'} />
      <Metric label="Call count" value={String(callCount)} />
      <Metric label="Tools" value={tools.length ? tools.join(', ') : '-'} />
      {evidence.length > 0 && (
        <div className="evidenceList">
          {evidence.map((item, index) => (
            <div key={`${item.tool}-${index}`} className="evidenceItem">
              <strong>{item.tool}</strong>
              <span>{item.summary}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusTile({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className={good ? 'statusTile good' : 'statusTile bad'}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CorrectionBadge({ detected, corrected, styleFixed }: { detected: number; corrected: number; styleFixed: boolean }) {
  if (detected === 0 && !styleFixed) return <span className="correctionTag clean">-</span>;
  if (detected > 0 && corrected === detected) return <span className="correctionTag fixed">{corrected} fixed</span>;
  if (detected > 0) return <span className="correctionTag failed">{detected - corrected} left</span>;
  if (styleFixed) return <span className="correctionTag fixed">style</span>;
  return null;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function labelFor(view: View) {
  return { documents: 'Documents', chunks: 'Chunks', ask: 'Ask', traces: 'Traces', evaluations: 'Evaluations', mcp: 'MCP' }[view];
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

async function copyJsonToClipboard(data: unknown) {
  const text = JSON.stringify(data, null, 2);
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

createRoot(document.getElementById('root')!).render(<App />);
