// src/pages/ResearchPage.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchArxiv } from '../api/stats';
import type { ArxivPaper } from '../types';
import { BookOpen, Search, ExternalLink, Database, Wifi, Clock } from 'lucide-react';

const MEDICAL_TOPICS = [
  'drug interactions clinical trial',
  'type 2 diabetes treatment',
  'chronic kidney disease nephrotoxic drugs',
  'warfarin anticoagulation adverse effects',
  'serotonin syndrome risk factors',
  'polypharmacy elderly patients',
];

export default function ResearchPage() {
  const [query, setQuery] = useState('');
  const [activeQuery, setActiveQuery] = useState('');

  const { data: papers, isFetching, error } = useQuery<ArxivPaper[]>({
    queryKey: ['arxiv', activeQuery],
    queryFn: () => searchArxiv(activeQuery),
    enabled: !!activeQuery,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const handleSearch = () => {
    if (query.trim()) setActiveQuery(query.trim());
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Search Input */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <BookOpen size={20} color="var(--accent-teal)" />
          <h2 style={{ fontSize: '1.1rem', margin: 0 }}>ArXiv Medical Research Search</h2>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search medical research papers…"
            onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
          />
          <button className="btn btn-primary" onClick={handleSearch} disabled={isFetching || !query.trim()}>
            {isFetching ? <><span className="spinner" /> Searching…</> : <><Search size={16} /> Search</>}
          </button>
        </div>
        {/* Topic chips */}
        <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {MEDICAL_TOPICS.map((t) => (
            <button key={t} className="btn btn-secondary btn-sm"
              style={{ fontSize: '0.75rem' }}
              onClick={() => { setQuery(t); setActiveQuery(t); }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && <div className="alert alert-error"><Search size={16} />{(error as Error).message}</div>}

      {/* Loading */}
      {isFetching && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton card" style={{ height: 130 }} />)}
        </div>
      )}

      {/* Results */}
      {papers && !isFetching && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h3 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
              {papers.length} papers for <em style={{ color: 'var(--accent-teal)' }}>"{activeQuery}"</em>
            </h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {papers.map((paper, i) => <PaperCard key={i} paper={paper} />)}
          </div>
        </>
      )}

      {!activeQuery && !isFetching && (
        <div className="card" style={{ textAlign: 'center', padding: '60px 40px' }}>
          <BookOpen size={48} color="rgba(0,212,255,0.2)" style={{ margin: '0 auto 16px' }} />
          <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
            Search for medical research papers — combines live arXiv API with Qdrant semantic cache.
          </p>
        </div>
      )}
    </div>
  );
}

function PaperCard({ paper }: { paper: ArxivPaper }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="card" style={{ gap: 12, display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: 6, color: 'var(--text-primary)', lineHeight: 1.4 }}>
            {paper.title}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginBottom: 8 }}>
            {paper.authors.slice(0, 3).join(', ')}{paper.authors.length > 3 ? ' et al.' : ''}
          </p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.84rem', lineHeight: 1.6 }}>
            {expanded ? paper.summary : `${paper.summary.slice(0, 220)}…`}
          </p>
          <button onClick={() => setExpanded(!expanded)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent-teal)', fontSize: '0.78rem', marginTop: 6, padding: 0 }}>
            {expanded ? 'Show less ↑' : 'Read more ↓'}
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-end', flexShrink: 0 }}>
          {paper.url && (
            <a href={paper.url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
              <ExternalLink size={13} /> arXiv
            </a>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            <Clock size={12} /> {paper.published}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {paper.source === 'qdrant_cache'
              ? <><Database size={12} color="var(--accent-purple)" /><span style={{ color: 'var(--accent-purple)', fontSize: '0.72rem' }}>Cached</span></>
              : <><Wifi size={12} color="var(--accent-green)" /><span style={{ color: 'var(--accent-green)', fontSize: '0.72rem' }}>Live API</span></>}
          </div>
          {paper.score && (
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Score: {paper.score.toFixed(3)}
            </span>
          )}
        </div>
      </div>
      {/* Topics */}
      {paper.topics.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {paper.topics.slice(0, 5).map((t) => <span key={t} className="badge badge-teal">{t}</span>)}
        </div>
      )}
    </div>
  );
}
