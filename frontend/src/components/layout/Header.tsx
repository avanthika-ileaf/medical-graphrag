// src/components/layout/Header.tsx
import { useLocation } from 'react-router-dom';
import { Activity, Wifi } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getGraphStats } from '../../api/stats';

const PAGE_TITLES: Record<string, { title: string; sub: string }> = {
  '/':          { title: 'Dashboard',         sub: 'System overview and quick queries' },
  '/query':     { title: 'Query Interface',   sub: 'GraphRAG vs Standard RAG comparison' },
  '/patients':  { title: 'Patient Registry',  sub: 'Browse and analyse patient profiles' },
  '/graph':     { title: 'Graph Explorer',    sub: 'Interactive knowledge graph visualisation' },
  '/research':  { title: 'Research Papers',   sub: 'ArXiv medical literature search' },
  '/analytics': { title: 'Analytics',         sub: 'Health metrics and KPI dashboard' },
};

export default function Header() {
  const { pathname } = useLocation();
  const meta = PAGE_TITLES[pathname] ?? { title: 'medknow', sub: '' };

  const { data: stats } = useQuery({
    queryKey: ['graph-stats'],
    queryFn: getGraphStats,
    staleTime: 60_000,
    retry: false,
  });

  const connected = !!stats;

  return (
    <header style={styles.header}>
      <div>
        <h1 style={styles.title}>{meta.title}</h1>
        {meta.sub && <p style={styles.sub}>{meta.sub}</p>}
      </div>
      <div style={styles.right}>
        {stats && (
          <div style={styles.pill}>
            <Activity size={12} color="#2ed573" />
            <span style={{ color: '#2ed573', fontSize: '0.75rem' }}>
              {stats.total_nodes.toLocaleString()} nodes
            </span>
          </div>
        )}
        <div style={{ ...styles.pill, borderColor: connected ? 'rgba(46,213,115,0.3)' : 'rgba(255,71,87,0.3)' }}>
          <Wifi size={12} color={connected ? '#2ed573' : '#ff4757'} />
          <span style={{ color: connected ? '#2ed573' : '#ff4757', fontSize: '0.75rem' }}>
            {connected ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>
    </header>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    position: 'fixed',
    top: 0,
    left: 'var(--sidebar-width)',
    right: 0,
    height: 'var(--header-height)',
    background: 'rgba(6, 13, 26, 0.85)',
    backdropFilter: 'blur(16px)',
    borderBottom: '1px solid rgba(255,255,255,0.07)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 36px',
    zIndex: 90,
  },
  title: { fontSize: '1.05rem', fontWeight: 700, color: '#f0f4ff', margin: 0 },
  sub: { fontSize: '0.75rem', color: '#4a5980', margin: 0, marginTop: 2 },
  right: { display: 'flex', alignItems: 'center', gap: 10 },
  pill: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '5px 12px',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(46,213,115,0.2)',
    borderRadius: 100,
  },
};
