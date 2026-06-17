// src/pages/Dashboard.tsx
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getGraphStats } from '../api/stats';
import { getHighRiskPatients } from '../api/patients';
import { getPresets } from '../api/query';
import { Users, Pill, Activity, GitBranch, AlertTriangle, Search, ArrowRight, Zap } from 'lucide-react';
import { useQueryStore } from '../store/queryStore';

export default function Dashboard() {
  const navigate = useNavigate();
  const setCurrentQuery = useQueryStore((s) => s.setCurrentQuery);

  const { data: stats } = useQuery({ queryKey: ['graph-stats'], queryFn: getGraphStats, retry: false });
  const { data: highRisk } = useQuery({ queryKey: ['high-risk', 10], queryFn: () => getHighRiskPatients(6), retry: false });
  const { data: presets } = useQuery({ queryKey: ['presets'], queryFn: getPresets, retry: false });

  const handlePreset = (q: string) => {
    setCurrentQuery(q);
    navigate('/query');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Hero */}
      <div style={styles.hero}>
        <div style={styles.heroBadge}>
          <Zap size={12} />
          <span>Medical Knowledge GraphRAG Platform</span>
        </div>
        <h1 style={styles.heroTitle}>
          Hybrid Graph + Vector<br />
          <span style={{ color: 'var(--accent-teal)' }}>Medical Intelligence</span>
        </h1>
        <p style={styles.heroSub}>
          Multi-hop reasoning over Neo4j knowledge graphs + Qdrant semantic search,
          powered by LiteLLM for provider-agnostic LLM generation.
        </p>
        <button className="btn btn-primary btn-lg" onClick={() => navigate('/query')}>
          <Search size={18} /> Start Querying
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid-4">
        <StatCard icon={<Users size={20} />} label="Patients" value={stats?.nodes?.Patient?.toLocaleString() ?? '—'} sub="in Neo4j graph" color="teal" loading={!stats} />
        <StatCard icon={<Pill size={20} />} label="Drugs" value={stats?.nodes?.Drug?.toLocaleString() ?? '—'} sub="unique medications" color="purple" loading={!stats} />
        <StatCard icon={<Activity size={20} />} label="Conditions" value={stats?.nodes?.Condition?.toLocaleString() ?? '—'} sub="medical conditions" color="green" loading={!stats} />
        <StatCard icon={<GitBranch size={20} />} label="Relationships" value={stats?.total_relationships?.toLocaleString() ?? '—'} sub="graph edges" color="orange" loading={!stats} />
      </div>

      <div className="grid-2">
        {/* Preset Queries */}
        <div className="card">
          <div className="section-header">
            <div className="section-title"><Search size={18} className="icon" /> Preset Queries</div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(presets ?? FALLBACK_PRESETS).map((q, i) => (
              <button key={i} style={styles.presetBtn} onClick={() => handlePreset(q)}>
                <span style={styles.presetNum}>{String(i + 1).padStart(2, '0')}</span>
                <span style={{ flex: 1, textAlign: 'left', fontSize: '0.855rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{q}</span>
                <ArrowRight size={14} color="var(--accent-teal)" style={{ opacity: 0, transition: '0.15s' }} className="preset-arrow" />
              </button>
            ))}
          </div>
        </div>

        {/* High Risk Patients */}
        <div className="card">
          <div className="section-header">
            <div className="section-title"><AlertTriangle size={18} className="icon" /> High-Risk Patients</div>
            <button className="btn btn-secondary btn-sm" onClick={() => navigate('/patients')}>View All</button>
          </div>
          {!highRisk ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 52 }} />)}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {highRisk.slice(0, 5).map((p) => (
                <div key={p.patientID} style={styles.patientRow} onClick={() => navigate(`/patients`)}>
                  <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.875rem' }}>{p.name || p.patientID}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      {p.age} · {p.drugCount} drugs · {p.interactions.length} interactions
                    </span>
                  </div>
                  <span className={`badge badge-${p.risk_level}`}>{p.risk_level}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Relationship counts */}
      {stats && (
        <div className="card">
          <div className="section-title mb-4"><GitBranch size={18} className="icon" /> Relationship Breakdown</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            {Object.entries(stats.relationships).map(([rel, count]) => (
              <div key={rel} style={styles.relCard}>
                <span style={styles.relCount}>{count.toLocaleString()}</span>
                <span style={styles.relName}>{rel.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, sub, color, loading }: {
  icon: React.ReactNode; label: string; value: string;
  sub: string; color: string; loading: boolean;
}) {
  const colorMap: Record<string, string> = {
    teal: 'var(--accent-teal)', purple: 'var(--accent-purple)',
    green: 'var(--accent-green)', orange: 'var(--accent-orange)',
  };
  const c = colorMap[color] ?? 'var(--accent-teal)';
  return (
    <div className="stat-card">
      <div style={{ color: c, opacity: 0.9 }}>{icon}</div>
      <div className="stat-label">{label}</div>
      {loading
        ? <div className="skeleton" style={{ height: 36, width: 100 }} />
        : <div className="stat-value" style={{ color: c }}>{value}</div>}
      <div className="stat-sub">{sub}</div>
    </div>
  );
}

const FALLBACK_PRESETS = [
  'Which patients with Type 2 Diabetes are on 3+ medications that interact dangerously?',
  'Which patients with Chronic Kidney Disease are taking contraindicated drugs?',
  'Show the drug interaction chain from Warfarin (2 hops).',
  'Find patients sharing a doctor who have overlapping conditions and interacting drugs.',
  'Which patients are at risk for serotonin syndrome from their medications?',
];

const styles: Record<string, React.CSSProperties> = {
  hero: {
    display: 'flex', flexDirection: 'column', gap: 16,
    padding: '40px 40px 36px',
    background: 'linear-gradient(135deg, rgba(0,212,255,0.06) 0%, rgba(10,22,45,0.8) 60%)',
    border: '1px solid rgba(0,212,255,0.15)',
    borderRadius: 'var(--radius-xl)',
    backdropFilter: 'blur(12px)',
  },
  heroBadge: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '4px 12px', borderRadius: 100,
    background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.25)',
    color: 'var(--accent-teal)', fontSize: '0.72rem', fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '0.05em', width: 'fit-content',
  },
  heroTitle: { fontSize: '2.2rem', fontWeight: 800, lineHeight: 1.2, color: 'var(--text-primary)' },
  heroSub: { color: 'var(--text-secondary)', maxWidth: 560, lineHeight: 1.7, fontSize: '0.95rem' },
  presetBtn: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '12px 14px',
    background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)', cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  presetNum: {
    fontFamily: 'var(--font-mono)', fontSize: '0.72rem',
    color: 'var(--accent-teal)', opacity: 0.7, flexShrink: 0,
  },
  patientRow: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '10px 12px',
    background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)', cursor: 'pointer',
    transition: 'background 0.15s',
  },
  relCard: {
    display: 'flex', flexDirection: 'column', gap: 4, padding: '12px 16px',
    background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)', minWidth: 140,
  },
  relCount: { fontSize: '1.3rem', fontWeight: 700, color: 'var(--accent-teal)' },
  relName: { fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' },
};
