// src/pages/PatientsPage.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getHighRiskPatients, getContraindicatedPatients, getPatientProfile, getPatientGraphPath } from '../api/patients';
import type { PatientSummary, PatientProfile, PatientGraphPath } from '../types';
import { AlertTriangle, Shield, X, Pill, Activity, User, GitBranch } from 'lucide-react';

type FilterType = 'high-risk' | 'contraindicated';

export default function PatientsPage() {
  const [filter, setFilter] = useState<FilterType>('high-risk');
  const [selected, setSelected] = useState<PatientSummary | null>(null);
  const [search, setSearch] = useState('');

  const { data: highRisk, isLoading: hrLoading } = useQuery({
    queryKey: ['patients-high-risk'], queryFn: () => getHighRiskPatients(40), retry: false,
  });
  const { data: contra, isLoading: cLoading } = useQuery({
    queryKey: ['patients-contra'], queryFn: () => getContraindicatedPatients(40), retry: false,
  });

  const patients = (filter === 'high-risk' ? highRisk : contra) ?? [];
  const isLoading = filter === 'high-risk' ? hrLoading : cLoading;

  const filtered = patients.filter(
    (p) =>
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.patientID?.toLowerCase().includes(search.toLowerCase()) ||
      p.conditions?.some((c) => c.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div className="tabs" style={{ marginBottom: 0, flex: 'none' }}>
          <button className={`tab-btn ${filter === 'high-risk' ? 'active' : ''}`} onClick={() => setFilter('high-risk')}>
            <AlertTriangle size={14} /> High Risk
          </button>
          <button className={`tab-btn ${filter === 'contraindicated' ? 'active' : ''}`} onClick={() => setFilter('contraindicated')}>
            <Shield size={14} /> Contraindicated
          </button>
        </div>
        <input
          className="input"
          style={{ maxWidth: 300 }}
          placeholder="Search by name, ID, or condition…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginLeft: 'auto' }}>
          {filtered.length} patients
        </span>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {isLoading ? (
          <div style={{ padding: 40, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[...Array(6)].map((_, i) => <div key={i} className="skeleton" style={{ height: 56 }} />)}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Patient</th><th>Age</th><th>Gender</th>
                  <th>Drugs</th><th>Conditions</th><th>Interactions</th><th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr key={p.patientID} onClick={() => setSelected(p)}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.name || '—'}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{p.patientID}</div>
                    </td>
                    <td>{p.age ?? '—'}</td>
                    <td style={{ textTransform: 'capitalize' }}>{p.gender ?? '—'}</td>
                    <td>
                      <span style={{ background: 'rgba(0,212,255,0.1)', color: 'var(--accent-teal)', padding: '2px 8px', borderRadius: 100, fontSize: '0.8rem', fontWeight: 600 }}>
                        {p.drugCount ?? p.drugs?.length ?? '—'}
                      </span>
                    </td>
                    <td style={{ maxWidth: 200 }}>{p.conditions?.slice(0, 2).join(', ')}{p.conditions?.length > 2 ? '…' : ''}</td>
                    <td>
                      {p.interactions?.length > 0
                        ? <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>{p.interactions.length} ⚠</span>
                        : <span style={{ color: 'var(--text-muted)' }}>0</span>}
                    </td>
                    <td><span className={`badge badge-${p.risk_level}`}>{p.risk_level}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Patient Detail Modal */}
      {selected && <PatientModal patient={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function PatientModal({ patient, onClose }: { patient: PatientSummary; onClose: () => void }) {
  const { data: profile } = useQuery<PatientProfile>({
    queryKey: ['patient-profile', patient.patientID],
    queryFn: () => getPatientProfile(patient.patientID),
    retry: false,
  });

  const { data: graphPath } = useQuery<PatientGraphPath>({
    queryKey: ['patient-path', patient.patientID],
    queryFn: () => getPatientGraphPath(patient.patientID),
    retry: false,
  });

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.modalHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={styles.avatar}><User size={22} color="var(--accent-teal)" /></div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.2rem' }}>{profile?.name || patient.name || 'Patient'}</h2>
              <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{patient.patientID}</p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span className={`badge badge-${patient.risk_level}`}>{patient.risk_level} risk</span>
            <button style={styles.closeBtn} onClick={onClose}><X size={20} /></button>
          </div>
        </div>

        <div style={styles.modalBody}>
          {/* Demographics */}
          <div className="grid-4" style={{ gap: 12, marginBottom: 20 }}>
            {[
              { label: 'Age', value: profile?.age ?? patient.age ?? '—' },
              { label: 'Gender', value: profile?.gender ?? patient.gender ?? '—' },
              { label: 'Drugs', value: profile?.drugs?.length ?? patient.drugCount ?? '—' },
              { label: 'Providers', value: profile?.providers?.length ?? '—' },
            ].map((m) => (
              <div key={m.label} style={{ background: 'var(--bg-glass)', padding: '12px 16px', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>{m.label}</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-teal)' }}>{m.value}</div>
              </div>
            ))}
          </div>

          <div className="grid-2">
            {/* Conditions */}
            <Section icon={<Activity size={16} />} title="Conditions">
              {profile?.conditions?.length
                ? profile.conditions.map((c) => (
                  <div key={c.name} style={styles.listItem}>
                    <span style={{ color: 'var(--text-primary)' }}>{c.name}</span>
                    {c.severity && <span className="badge badge-medium">sev {c.severity.toFixed(1)}</span>}
                  </div>
                ))
                : (patient.conditions ?? []).map((c) => <div key={c} style={styles.listItem}><span>{c}</span></div>)}
            </Section>

            {/* Drugs */}
            <Section icon={<Pill size={16} />} title="Medications">
              {profile?.drugs?.length
                ? profile.drugs.map((d) => (
                  <div key={d.name} style={styles.listItem}>
                    <span style={{ color: 'var(--text-primary)' }}>{d.name}</span>
                    {d.dosage && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{d.dosage}</span>}
                  </div>
                ))
                : (patient.drugs ?? []).map((d) => <div key={d} style={styles.listItem}><span>{d}</span></div>)}
            </Section>
          </div>

          {/* Interactions */}
          {(profile?.interactions?.length || patient.interactions?.length) ? (
            <Section icon={<AlertTriangle size={16} />} title="Drug Interactions" titleColor="var(--accent-red)">
              {(profile?.interactions ?? patient.interactions ?? []).map((ix, i) => (
                <div key={i} style={{ ...styles.listItem, borderColor: 'rgba(255,71,87,0.2)', background: 'rgba(255,71,87,0.05)' }}>
                  <span style={{ color: 'var(--text-primary)' }}>{ix.drug1} ↔ {ix.drug2}</span>
                  <span className="badge badge-high">sev {ix.severity.toFixed(2)}</span>
                </div>
              ))}
            </Section>
          ) : null}

          {/* Graph path summary */}
          {graphPath && graphPath.nodes.length > 0 && (
            <Section icon={<GitBranch size={16} />} title="Graph Connections">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {graphPath.nodes.map((n) => (
                  <span key={n.id} style={{
                    padding: '4px 10px', borderRadius: 100, fontSize: '0.75rem',
                    background: NODE_COLORS[n.type]?.bg ?? 'rgba(255,255,255,0.05)',
                    color: NODE_COLORS[n.type]?.text ?? '#8899bb',
                    border: `1px solid ${NODE_COLORS[n.type]?.border ?? 'rgba(255,255,255,0.1)'}`,
                  }}>
                    {n.type}: {n.label}
                  </span>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ icon, title, titleColor, children }: {
  icon: React.ReactNode; title: string; titleColor?: string; children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, color: titleColor ?? 'var(--accent-teal)' }}>
        {icon}<span style={{ fontWeight: 600, fontSize: '0.875rem', color: titleColor ?? 'var(--text-primary)' }}>{title}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>{children}</div>
    </div>
  );
}

const NODE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  Patient:  { bg: 'rgba(0,212,255,0.1)',   text: '#00d4ff', border: 'rgba(0,212,255,0.25)' },
  Drug:     { bg: 'rgba(255,165,2,0.1)',   text: '#ffa502', border: 'rgba(255,165,2,0.25)' },
  Condition:{ bg: 'rgba(46,213,115,0.1)',  text: '#2ed573', border: 'rgba(46,213,115,0.25)' },
  Provider: { bg: 'rgba(162,155,254,0.1)', text: '#a29bfe', border: 'rgba(162,155,254,0.25)' },
};

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
    backdropFilter: 'blur(6px)', zIndex: 200,
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
  },
  modal: {
    background: '#0a1628', border: '1px solid rgba(0,212,255,0.2)',
    borderRadius: 'var(--radius-xl)', width: '100%', maxWidth: 760,
    maxHeight: '88vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
    boxShadow: '0 24px 80px rgba(0,0,0,0.6)',
  },
  modalHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.07)',
  },
  modalBody: { padding: 24, overflowY: 'auto', flex: 1 },
  avatar: {
    width: 48, height: 48, borderRadius: 12,
    background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.25)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  closeBtn: {
    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 8, padding: 6, cursor: 'pointer', color: 'var(--text-muted)',
    display: 'flex', alignItems: 'center',
  },
  listItem: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '8px 12px', background: 'var(--bg-glass)',
    border: '1px solid var(--border-subtle)', borderRadius: 8, fontSize: '0.875rem',
  },
};
