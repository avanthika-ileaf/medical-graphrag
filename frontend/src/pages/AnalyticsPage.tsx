// src/pages/AnalyticsPage.tsx
import { useQuery } from '@tanstack/react-query';
import { getGraphStats, getDrugInteractions } from '../api/stats';
import { getHighRiskPatients } from '../api/patients';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { BarChart2, Activity, Shield, GitBranch } from 'lucide-react';

const TEAL_PALETTE = ['#00d4ff', '#0099bb', '#006688', '#003344', '#a29bfe', '#2ed573', '#ffa502', '#ff4757'];

export default function AnalyticsPage() {
  const { data: stats } = useQuery({ queryKey: ['graph-stats'], queryFn: getGraphStats, retry: false });
  const { data: interactions } = useQuery({ queryKey: ['drug-interactions-all'], queryFn: () => getDrugInteractions(0), retry: false });
  const { data: highRisk } = useQuery({ queryKey: ['patients-high-risk-analytics'], queryFn: () => getHighRiskPatients(50), retry: false });

  // Node distribution for pie chart
  const nodePie = stats
    ? Object.entries(stats.nodes).map(([name, value]) => ({ name, value }))
    : [];

  // Relationship counts for bar chart
  const relBar = stats
    ? Object.entries(stats.relationships).map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }))
    : [];

  // Severity distribution
  const sevBuckets = [
    { range: '0.5-0.6', count: 0 }, { range: '0.6-0.7', count: 0 },
    { range: '0.7-0.8', count: 0 }, { range: '0.8-0.9', count: 0 },
    { range: '0.9-1.0', count: 0 },
  ];
  (interactions ?? []).forEach((ix) => {
    const s = ix.severity;
    if (s >= 0.5 && s < 0.6) sevBuckets[0].count++;
    else if (s >= 0.6 && s < 0.7) sevBuckets[1].count++;
    else if (s >= 0.7 && s < 0.8) sevBuckets[2].count++;
    else if (s >= 0.8 && s < 0.9) sevBuckets[3].count++;
    else if (s >= 0.9) sevBuckets[4].count++;
  });

  // Age distribution
  const ageBuckets: Record<string, number> = {};
  (highRisk ?? []).forEach((p) => {
    if (!p.age) return;
    const bucket = `${Math.floor(p.age / 10) * 10}s`;
    ageBuckets[bucket] = (ageBuckets[bucket] ?? 0) + 1;
  });
  const ageData = Object.entries(ageBuckets).sort(([a], [b]) => parseInt(a) - parseInt(b)).map(([age, count]) => ({ age, count }));

  const highRiskCount = (highRisk ?? []).length;
  const avgInteractions = highRisk
    ? (highRisk.reduce((s, p) => s + (p.interactions?.length ?? 0), 0) / (highRisk.length || 1)).toFixed(1)
    : '—';

  const tooltip = { contentStyle: { background: '#0a1628', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f0f4ff', fontSize: 12 } };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* KPI row */}
      <div className="grid-4">
        <KPI icon={<BarChart2 size={20} />} label="Total Nodes" value={stats?.total_nodes?.toLocaleString() ?? '—'} color="var(--accent-teal)" loading={!stats} />
        <KPI icon={<GitBranch size={20} />} label="Total Edges" value={stats?.total_relationships?.toLocaleString() ?? '—'} color="var(--accent-purple)" loading={!stats} />
        <KPI icon={<Activity size={20} />} label="High-Risk Patients" value={highRiskCount.toString()} color="var(--accent-red)" loading={!highRisk} />
        <KPI icon={<Shield size={20} />} label="Avg Interactions/Patient" value={avgInteractions} color="var(--accent-orange)" loading={!highRisk} />
      </div>

      <div className="grid-2">
        {/* Node Type Distribution */}
        <div className="card">
          <div className="section-title mb-4"><BarChart2 size={18} className="icon" /> Node Type Distribution</div>
          {nodePie.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={nodePie} cx="50%" cy="50%" outerRadius={90} dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                  {nodePie.map((_, i) => <Cell key={i} fill={TEAL_PALETTE[i % TEAL_PALETTE.length]} />)}
                </Pie>
                <Tooltip {...tooltip} />
                <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className="skeleton" style={{ height: 240 }} />}
        </div>

        {/* Relationship Type Breakdown */}
        <div className="card">
          <div className="section-title mb-4"><GitBranch size={18} className="icon" /> Relationship Counts</div>
          {relBar.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={relBar} layout="vertical">
                <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis dataKey="name" type="category" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} width={140} />
                <Tooltip {...tooltip} />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="url(#relGrad)" />
                <defs>
                  <linearGradient id="relGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#0084a6" /><stop offset="100%" stopColor="#00d4ff" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="skeleton" style={{ height: 240 }} />}
        </div>
      </div>

      <div className="grid-2">
        {/* Severity Distribution */}
        <div className="card">
          <div className="section-title mb-4"><Activity size={18} className="icon" /> Interaction Severity Distribution</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={sevBuckets}>
              <XAxis dataKey="range" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...tooltip} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {sevBuckets.map((b, i) => {
                  const pct = parseFloat(b.range) - 0.5;
                  const color = pct < 0.2 ? '#2ed573' : pct < 0.3 ? '#ffa502' : '#ff4757';
                  return <Cell key={i} fill={color} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Age Distribution */}
        <div className="card">
          <div className="section-title mb-4"><Activity size={18} className="icon" /> Age Distribution (High-Risk Patients)</div>
          {ageData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={ageData}>
                <XAxis dataKey="age" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip {...tooltip} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} fill="url(#ageGrad)" />
                <defs>
                  <linearGradient id="ageGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#a29bfe" /><stop offset="100%" stopColor="#6c5ce7" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="skeleton" style={{ height: 220 }} />}
        </div>
      </div>
    </div>
  );
}

function KPI({ icon, label, value, color, loading }: { icon: React.ReactNode; label: string; value: string; color: string; loading: boolean }) {
  return (
    <div className="stat-card">
      <div style={{ color }}>{icon}</div>
      <div className="stat-label">{label}</div>
      {loading ? <div className="skeleton" style={{ height: 36, width: 80 }} />
        : <div className="stat-value" style={{ color }}>{value}</div>}
    </div>
  );
}
