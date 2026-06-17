// src/components/layout/Sidebar.tsx
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Search, Users, GitBranch,
  BookOpen, BarChart2, Activity, Dna
} from 'lucide-react';

const navItems = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/query',     icon: Search,          label: 'Query'     },
  { to: '/patients',  icon: Users,           label: 'Patients'  },
  { to: '/graph',     icon: GitBranch,       label: 'Graph Explorer' },
  { to: '/research',  icon: BookOpen,        label: 'Research'  },
  { to: '/analytics', icon: BarChart2,       label: 'Analytics' },
];

export default function Sidebar() {
  return (
    <aside style={styles.sidebar}>
      {/* Logo */}
      <div style={styles.logo}>
        <div style={styles.logoIcon}>
          <Dna size={22} color="#00d4ff" />
        </div>
        <div>
          <div style={styles.logoTitle}>medknow</div>
          <div style={styles.logoSub}>Knowledge Intelligence</div>
        </div>
      </div>

      <div style={styles.glow} />

      {/* Nav */}
      <nav style={styles.nav}>
        <div style={styles.navGroup}>
          <div style={styles.navGroupLabel}>Navigation</div>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              style={({ isActive }) => ({
                ...styles.navItem,
                ...(isActive ? styles.navItemActive : {}),
              })}
            >
              {({ isActive }) => (
                <>
                  <span style={{ ...styles.navIcon, ...(isActive ? styles.navIconActive : {}) }}>
                    <Icon size={18} />
                  </span>
                  <span style={styles.navLabel}>{label}</span>
                  {isActive && <span style={styles.navDot} />}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Stack badge */}
      <div style={styles.stackBadge}>
        <Activity size={12} color="#00d4ff" />
        <span style={styles.stackText}>Neo4j · Qdrant · LiteLLM</span>
      </div>
    </aside>
  );
}

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    position: 'fixed',
    top: 0, left: 0, bottom: 0,
    width: 'var(--sidebar-width)',
    background: 'linear-gradient(180deg, #080f1f 0%, #060c19 100%)',
    borderRight: '1px solid rgba(255,255,255,0.07)',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 100,
    overflowY: 'auto',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '24px 20px 20px',
  },
  logoIcon: {
    width: 40, height: 40,
    background: 'rgba(0,212,255,0.12)',
    border: '1px solid rgba(0,212,255,0.25)',
    borderRadius: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  logoTitle: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: '#f0f4ff',
    lineHeight: 1.2,
  },
  logoSub: {
    fontSize: '0.7rem',
    color: '#4a5980',
    marginTop: 2,
  },
  glow: {
    height: 1,
    background: 'linear-gradient(90deg, transparent, rgba(0,212,255,0.3), transparent)',
    margin: '0 16px 16px',
  },
  nav: { flex: 1, padding: '0 10px' },
  navGroup: { marginBottom: 24 },
  navGroupLabel: {
    fontSize: '0.65rem',
    fontWeight: 600,
    color: '#4a5980',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: '0 10px',
    marginBottom: 6,
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '9px 10px',
    borderRadius: 8,
    color: '#8899bb',
    textDecoration: 'none',
    fontSize: '0.875rem',
    fontWeight: 500,
    transition: 'all 150ms ease',
    marginBottom: 2,
    position: 'relative',
  },
  navItemActive: {
    background: 'rgba(0,212,255,0.1)',
    color: '#00d4ff',
    border: '1px solid rgba(0,212,255,0.18)',
  },
  navIcon: { opacity: 0.6, display: 'flex', transition: 'opacity 150ms ease' },
  navIconActive: { opacity: 1 },
  navLabel: { flex: 1 },
  navDot: {
    width: 6, height: 6,
    borderRadius: '50%',
    background: '#00d4ff',
    boxShadow: '0 0 8px rgba(0,212,255,0.8)',
  },
  stackBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    margin: 16,
    padding: '8px 12px',
    background: 'rgba(0,212,255,0.05)',
    border: '1px solid rgba(0,212,255,0.12)',
    borderRadius: 8,
  },
  stackText: {
    fontSize: '0.67rem',
    color: '#4a5980',
    fontFamily: 'var(--font-mono)',
  },
};
