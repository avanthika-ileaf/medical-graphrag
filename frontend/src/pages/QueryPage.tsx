// src/pages/QueryPage.tsx
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { compareQuery } from '../api/query';
import { useQueryStore } from '../store/queryStore';
import type { CompareQueryResponse } from '../types';
import {
  Search, Zap, Brain, ChevronDown, ChevronUp,
  Clock, AlertCircle, ExternalLink, BookOpen
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const PRESETS = [
  'Which patients with Type 2 Diabetes are on 3+ medications that interact dangerously?',
  'Which patients with Chronic Kidney Disease are taking contraindicated drugs?',
  'Show the drug interaction chain from Warfarin (2 hops).',
  'Find patients sharing a doctor who have overlapping conditions and interacting drugs.',
];

export default function QueryPage() {
  const { currentQuery, setCurrentQuery, addToHistory } = useQueryStore();
  const [input, setInput] = useState(currentQuery);
  const [result, setResult] = useState<CompareQueryResponse | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const mutation = useMutation({
    mutationFn: compareQuery,
    onSuccess: (data) => {
      setResult(data);
      addToHistory({
        id: Date.now().toString(),
        query: data.query,
        timestamp: new Date(),
        answer: data.graph_rag.answer,
        confidence: data.graph_rag.confidence,
        latency_ms: data.graph_rag.latency_ms,
      });
    },
  });

  const handleRun = () => {
    if (!input.trim()) return;
    setCurrentQuery(input);
    mutation.mutate(input.trim());
  };


  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Query Input */}
      <div className="card card-lg">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <Search size={20} color="var(--accent-teal)" />
          <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Medical Query Interface</h2>
        </div>
        <textarea
          className="textarea"
          style={{ minHeight: 110, fontSize: '0.95rem' }}
          placeholder="e.g. Which patients with Type 2 Diabetes are on 3+ medications that interact dangerously?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && e.ctrlKey) handleRun(); }}
        />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 14 }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Ctrl+Enter to run</span>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-secondary" onClick={() => setInput('')}>Clear</button>
            <button className="btn btn-primary btn-lg" onClick={handleRun} disabled={mutation.isPending || !input.trim()}>
              {mutation.isPending ? <><span className="spinner" /> Running...</> : <><Zap size={16} /> Run Comparison</>}
            </button>
          </div>
        </div>

        {/* Presets */}
        <div style={{ marginTop: 16 }}>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Quick Presets</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {PRESETS.map((p, i) => (
              <button key={i} className="btn btn-secondary btn-sm" style={{ fontSize: '0.75rem', maxWidth: 280, textAlign: 'left', whiteSpace: 'normal', height: 'auto', padding: '6px 12px' }}
                onClick={() => setInput(p)}>
                {p.slice(0, 55)}…
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {mutation.isError && (
        <div className="alert alert-error">
          <AlertCircle size={16} />
          <span>{(mutation.error as Error).message}</span>
        </div>
      )}

      {/* Loading */}
      {mutation.isPending && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, padding: 48 }}>
          <span className="spinner spinner-lg" />
          <p style={{ color: 'var(--text-secondary)' }}>Running retrieval pipelines… this may take 15–30s</p>
        </div>
      )}

      {/* Results */}
      {result && !mutation.isPending && (
        <>
          {/* Side-by-side comparison */}
          <div className="grid-2">
            <AnswerCard
              title="Standard RAG"
              subtitle="Vector-only (Qdrant)"
              icon={<Brain size={18} />}
              answer={result.standard_rag.answer}
              confidence={result.standard_rag.confidence}
              latency={result.standard_rag.latency_ms}
              color="#a29bfe"
              type="standard"
            />
            <AnswerCard
              title="GraphRAG"
              subtitle="Graph + Vector (Neo4j + Qdrant)"
              icon={<Zap size={18} />}
              answer={result.graph_rag.answer}
              confidence={result.graph_rag.confidence}
              latency={result.graph_rag.latency_ms}
              color="var(--accent-teal)"
              type="graph"
            />
          </div>

          {/* Latency chart */}
          <div className="card">
            <div className="section-title mb-4"><Clock size={18} className="icon" /> Latency Comparison</div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={[
                { name: 'Standard RAG', latency: result.standard_rag.latency_ms },
                { name: 'GraphRAG',     latency: result.graph_rag.latency_ms },
              ]}>
                <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} unit="ms" />
                <Tooltip contentStyle={{ background: '#0a1628', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f0f4ff' }} />
                <ReferenceLine y={2000} stroke="#ff4757" strokeDasharray="4 4" label={{ value: '2s target', fill: '#ff4757', fontSize: 11 }} />
                <Bar dataKey="latency" radius={[6, 6, 0, 0]} fill="url(#latencyGrad)" />
                <defs>
                  <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00d4ff" />
                    <stop offset="100%" stopColor="#0084a6" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Graph hits table */}
          {result.graph_hits.length > 0 && (
            <div className="card">
              <div className="section-title mb-4">Graph Traversal Results ({result.graph_hits.length})</div>
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>{Object.keys(result.graph_hits[0]).slice(0, 6).map(k => <th key={k}>{k}</th>)}</tr>
                  </thead>
                  <tbody>
                    {result.graph_hits.slice(0, 10).map((row, i) => (
                      <tr key={i}>
                        {Object.keys(result.graph_hits[0]).slice(0, 6).map(k => (
                          <td key={k}>{formatCell(row[k])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ArXiv papers */}
          {result.arxiv_papers.length > 0 && (
            <div className="card">
              <div className="section-title mb-4"><BookOpen size={18} className="icon" /> Related Research ({result.arxiv_papers.length})</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {result.arxiv_papers.slice(0, 5).map((p, i) => (
                  <div key={i} style={styles.paper}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                      <div>
                        <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4, fontSize: '0.9rem' }}>{p.title}</p>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginBottom: 6 }}>
                          {p.authors.slice(0, 3).join(', ')}{p.authors.length > 3 ? ' et al.' : ''} · {p.published}
                        </p>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', lineHeight: 1.5 }}>{p.summary.slice(0, 200)}…</p>
                      </div>
                      {p.url && (
                        <a href={p.url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm" style={{ flexShrink: 0 }}>
                          <ExternalLink size={13} /> arXiv
                        </a>
                      )}
                    </div>
                    <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {p.topics.slice(0, 4).map((t) => <span key={t} className="badge badge-teal">{t}</span>)}
                      <span className="badge badge-purple">{p.source}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Provenance evidence */}
          <div className="card">
            <button style={styles.expandBtn} onClick={() => setShowEvidence(!showEvidence)}>
              <span style={{ fontWeight: 600 }}>Provenance & Evidence</span>
              {showEvidence ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {showEvidence && (
              <div style={{ marginTop: 16 }} className="grid-2">
                <div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: 8 }}>GRAPH-ONLY</p>
                  {result.graph_rag.provenance.graph_only.length
                    ? result.graph_rag.provenance.graph_only.map((id) => <div key={id} style={styles.provChip}>{id}</div>)
                    : <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>None</span>}
                </div>
                <div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: 8 }}>CONFIRMED BY BOTH</p>
                  {result.graph_rag.provenance.confirmed.length
                    ? result.graph_rag.provenance.confirmed.map((id) => <div key={id} style={{ ...styles.provChip, borderColor: 'rgba(46,213,115,0.3)', color: 'var(--accent-green)' }}>{id}</div>)
                    : <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>None</span>}
                </div>
              </div>
            )}
          </div>

          {/* Raw agent output */}
          {result.graph_rag.agent_output && (
            <div className="card">
              <button style={styles.expandBtn} onClick={() => setShowRaw(!showRaw)}>
                <span style={{ fontWeight: 600 }}>Raw Agent Output</span>
                {showRaw ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              {showRaw && (
                <pre style={styles.rawOutput}>{result.graph_rag.agent_output}</pre>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function AnswerCard({ title, subtitle, icon, answer, confidence, latency, color, type }: {
  title: string; subtitle: string; icon: React.ReactNode;
  answer: string; confidence: number; latency: number;
  color: string; type: 'standard' | 'graph';
}) {
  const level = confidence >= 0.7 ? 'high' : confidence >= 0.4 ? 'medium' : 'low';
  return (
    <div className="card" style={{ borderColor: type === 'graph' ? 'rgba(0,212,255,0.2)' : 'rgba(162,155,254,0.15)', display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ color }}>{icon}</span>
        <div>
          <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.95rem' }}>{title}</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{subtitle}</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 16 }}>
        <div style={styles.metric}><span style={{ color, fontSize: '1.1rem', fontWeight: 700 }}>{Math.round(confidence * 100)}%</span><span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>Confidence</span></div>
        <div style={styles.metric}><span style={{ color, fontSize: '1.1rem', fontWeight: 700 }}>{latency.toFixed(0)}<span style={{ fontSize: '0.7rem' }}>ms</span></span><span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>Latency</span></div>
      </div>
      <div className="progress-bar"><div className={`progress-fill ${level}`} style={{ width: `${confidence * 100}%` }} /></div>
      <div style={styles.answerBox}>{answer || 'No answer returned.'}</div>
    </div>
  );
}

function formatCell(v: unknown): React.ReactNode {
  if (v === null || v === undefined) return '—';

  // Helper for single drug interaction object formatting
  const renderInteraction = (item: any, idx?: number) => {
    const drug1 = String(item.drug1 || '');
    const drug2 = String(item.drug2 || '');
    const severity = item.severity;
    
    // Determine badge level based on severity
    let badgeClass = 'badge-medium';
    if (typeof severity === 'number') {
      if (severity >= 0.7) badgeClass = 'badge-high';
      else if (severity < 0.4) badgeClass = 'badge-low';
    }

    return (
      <div 
        key={idx} 
        style={{ 
          display: 'inline-flex', 
          alignItems: 'center', 
          gap: 6,
          background: 'var(--bg-glass)',
          border: '1px solid var(--border-subtle)',
          padding: '4px 10px',
          borderRadius: 8,
          fontSize: '0.8rem',
          margin: '2px',
          whiteSpace: 'nowrap'
        }}
      >
        <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{drug1} ↔ {drug2}</span>
        {typeof severity === 'number' && (
          <span className={`badge ${badgeClass}`} style={{ textTransform: 'lowercase', padding: '1px 6px', fontSize: '0.7rem' }}>
            sev {severity.toFixed(2)}
          </span>
        )}
      </div>
    );
  };

  if (Array.isArray(v)) {
    if (v.length === 0) return '—';
    
    // Check if the array contains drug interaction objects
    const isInteractionArray = v.length > 0 && v[0] && typeof v[0] === 'object' && 'drug1' in v[0] && 'drug2' in v[0];
    
    if (isInteractionArray) {
      return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxWidth: 450 }}>
          {v.slice(0, 3).map((item, idx) => renderInteraction(item, idx))}
          {v.length > 3 && (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem', alignSelf: 'center', marginLeft: 4 }}>
              +{v.length - 3} more
            </span>
          )}
        </div>
      );
    }

    // Default formatting for other arrays (like conditions or drugs list)
    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxWidth: 350 }}>
        {v.slice(0, 3).map((item, idx) => {
          const strItem = String(item);
          if (strItem.includes('↔')) {
            return (
              <div 
                key={idx}
                style={{ 
                  display: 'inline-flex', 
                  alignItems: 'center', 
                  background: 'rgba(255,165,2,0.1)',
                  border: '1px solid rgba(255,165,2,0.25)',
                  padding: '4px 10px',
                  borderRadius: 8,
                  fontSize: '0.8rem',
                  margin: '2px',
                  whiteSpace: 'nowrap'
                }}
              >
                <span style={{ color: 'var(--accent-orange)', fontWeight: 500 }}>{strItem}</span>
              </div>
            );
          }
          return (
            <span 
              key={idx} 
              className="badge badge-teal" 
              style={{ 
                textTransform: 'none', 
                fontSize: '0.78rem', 
                padding: '2px 8px',
                borderRadius: 6 
              }}
            >
              {strItem}
            </span>
          );
        })}
        {v.length > 3 && (
          <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem', alignSelf: 'center', marginLeft: 4 }}>
            +{v.length - 3} more
          </span>
        )}
      </div>
    );
  }

  if (typeof v === 'object') {
    // If it's a single interaction object
    if ('drug1' in v && 'drug2' in v) {
      return renderInteraction(v);
    }
    return <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{JSON.stringify(v).slice(0, 60)}</span>;
  }

  // If the string itself represents a formatted interaction like "A ↔ B"
  const strVal = String(v);
  if (strVal.includes('↔')) {
    return (
      <div 
        style={{ 
          display: 'inline-flex', 
          alignItems: 'center', 
          background: 'rgba(255,165,2,0.1)',
          border: '1px solid rgba(255,165,2,0.25)',
          padding: '4px 10px',
          borderRadius: 8,
          fontSize: '0.8rem',
          whiteSpace: 'nowrap'
        }}
      >
        <span style={{ color: 'var(--accent-orange)', fontWeight: 500 }}>{strVal}</span>
      </div>
    );
  }

  return strVal;
}

const styles: Record<string, React.CSSProperties> = {
  paper: {
    padding: 16, background: 'var(--bg-glass)',
    border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)',
  },
  expandBtn: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    width: '100%', background: 'none', border: 'none', cursor: 'pointer',
    color: 'var(--text-primary)', padding: 0,
  },
  provChip: {
    display: 'inline-block', padding: '3px 10px', margin: '3px',
    background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.2)',
    borderRadius: 100, fontSize: '0.75rem', color: 'var(--accent-teal)',
    fontFamily: 'var(--font-mono)',
  },
  rawOutput: {
    marginTop: 16, padding: 16, background: '#020810',
    border: '1px solid var(--border-subtle)', borderRadius: 8,
    fontSize: '0.78rem', color: 'var(--text-secondary)',
    whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 400, overflowY: 'auto',
  },
  metric: { display: 'flex', flexDirection: 'column', gap: 2 },
  answerBox: {
    padding: 14, background: 'rgba(0,0,0,0.3)', borderRadius: 8,
    fontSize: '0.875rem', color: 'var(--text-secondary)',
    lineHeight: 1.7, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
    maxHeight: 280, overflowY: 'auto',
  },
};
