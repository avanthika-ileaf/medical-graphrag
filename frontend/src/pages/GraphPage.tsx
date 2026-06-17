import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDrugInteractions, getKHopChain } from '../api/stats';
import { getPatientGraphPath } from '../api/patients';
import { getHighRiskPatients } from '../api/patients';
import { GitBranch, Search, Sliders } from 'lucide-react';

// Plotly for patient path graph
import _Plot from 'react-plotly.js';
const Plot = (_Plot as any).default || _Plot;

export default function GraphPage() {
  const [activeTab, setActiveTab] = useState<'interactions' | 'patient' | 'khop'>('interactions');
  const [severity, setSeverity] = useState(0.6);
  const [selectedPatient, setSelectedPatient] = useState('');
  const [khopDrug, setKhopDrug] = useState('Warfarin');
  const [khopK, setKhopK] = useState(2);

  const { data: interactions, isLoading: intLoading } = useQuery({
    queryKey: ['drug-interactions', severity],
    queryFn: () => getDrugInteractions(severity),
    retry: false,
  });

  const { data: patients } = useQuery({
    queryKey: ['patients-high-risk-graph'],
    queryFn: () => getHighRiskPatients(30),
    retry: false,
  });

  const { data: patientPath, isFetching: pathLoading } = useQuery({
    queryKey: ['patient-path', selectedPatient],
    queryFn: () => getPatientGraphPath(selectedPatient),
    enabled: !!selectedPatient,
    retry: false,
  });

  const { data: khopData, refetch: runKhop, isFetching: khopLoading } = useQuery({
    queryKey: ['khop', khopDrug, khopK],
    queryFn: () => getKHopChain(khopDrug, khopK),
    enabled: false,
    retry: false,
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Tabs */}
      <div className="tabs">
        <button className={`tab-btn ${activeTab === 'interactions' ? 'active' : ''}`} onClick={() => setActiveTab('interactions')}>
          Drug Interaction Network
        </button>
        <button className={`tab-btn ${activeTab === 'patient' ? 'active' : ''}`} onClick={() => setActiveTab('patient')}>
          Patient Path Visualiser
        </button>
        <button className={`tab-btn ${activeTab === 'khop' ? 'active' : ''}`} onClick={() => setActiveTab('khop')}>
          k-Hop Chain Explorer
        </button>
      </div>

      {/* Drug Interaction Network */}
      {activeTab === 'interactions' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Sliders size={16} color="var(--accent-teal)" />
            <label style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              Min severity: <strong style={{ color: 'var(--accent-teal)' }}>{severity.toFixed(1)}</strong>
            </label>
            <input type="range" min={0} max={1} step={0.1} value={severity}
              onChange={(e) => setSeverity(parseFloat(e.target.value))}
              style={{ width: 160, accentColor: 'var(--accent-teal)' }} />
          </div>

          {intLoading ? (
            <div className="card" style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="spinner spinner-lg" />
            </div>
          ) : interactions && interactions.length > 0 ? (
            <DrugInteractionPlot interactions={interactions} />
          ) : (
            <div className="alert alert-info"><GitBranch size={16} /> No interactions above severity {severity.toFixed(1)}</div>
          )}
        </div>
      )}

      {/* Patient Path */}
      {activeTab === 'patient' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <select className="select" style={{ maxWidth: 300 }} value={selectedPatient}
              onChange={(e) => setSelectedPatient(e.target.value)}>
              <option value="">Select a patient…</option>
              {(patients ?? []).map((p) => (
                <option key={p.patientID} value={p.patientID}>{p.name || p.patientID} ({p.patientID})</option>
              ))}
            </select>
          </div>

          {pathLoading && <div className="card" style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><span className="spinner spinner-lg" /></div>}
          {patientPath && !pathLoading && <PatientPathPlot path={patientPath} patientId={selectedPatient} />}
          {!selectedPatient && <div className="alert alert-info"><GitBranch size={16} /> Select a patient to visualise their knowledge graph path.</div>}
        </div>
      )}

      {/* k-Hop */}
      {activeTab === 'khop' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <input className="input" style={{ maxWidth: 200 }} value={khopDrug}
              onChange={(e) => setKhopDrug(e.target.value)} placeholder="Drug name (e.g. Warfarin)" />
            <select className="select" style={{ maxWidth: 120 }} value={khopK}
              onChange={(e) => setKhopK(parseInt(e.target.value))}>
              {[1, 2, 3, 4].map((k) => <option key={k} value={k}>{k} hops</option>)}
            </select>
            <button className="btn btn-primary" onClick={() => runKhop()} disabled={khopLoading}>
              {khopLoading ? <><span className="spinner" /> Running…</> : <><Search size={15} /> Explore Chain</>}
            </button>
          </div>

          {khopData && (
            <div className="card">
              <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
                Found <strong style={{ color: 'var(--accent-teal)' }}>{khopData.length}</strong> chains from <strong style={{ color: 'var(--text-primary)' }}>{khopDrug}</strong>
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {khopData.map((chain, i) => (
                  <div key={i} style={styles.chainRow}>
                    <span className="badge badge-teal">{chain.hops} hop{chain.hops > 1 ? 's' : ''}</span>
                    <div style={{ flex: 1 }}>
                      {chain.chain.map((drug, j) => (
                        <span key={j}>
                          <span style={{ color: 'var(--text-primary)', fontWeight: j === 0 ? 700 : 400 }}>{drug}</span>
                          {j < chain.chain.length - 1 && (
                            <span style={{ color: 'var(--accent-red)', margin: '0 8px' }}>
                              ↔ <span style={{ fontSize: '0.7rem' }}>({chain.severities[j]?.toFixed(2)})</span>
                            </span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DrugInteractionPlot({ interactions }: { interactions: { drug1: string; drug2: string; severity: number; mechanism: string }[] }) {
  const nodes = Array.from(new Set(interactions.flatMap((i) => [i.drug1, i.drug2])));
  const nodeIdx: Record<string, number> = Object.fromEntries(nodes.map((n, i) => [n, i]));
  const angle = (i: number) => (2 * Math.PI * i) / nodes.length;
  const r = 3;
  const positions = nodes.map((_, i) => ({ x: r * Math.cos(angle(i)), y: r * Math.sin(angle(i)) }));

  const edgeTraces = interactions.map((ix) => {
    const src = positions[nodeIdx[ix.drug1]];
    const tgt = positions[nodeIdx[ix.drug2]];
    const color = ix.severity >= 0.8 ? '#ff4757' : ix.severity >= 0.65 ? '#ffa502' : '#00d4ff';
    return {
      type: 'scatter' as const, mode: 'lines' as const,
      x: [src.x, tgt.x, null], y: [src.y, tgt.y, null],
      line: { width: Math.max(1.5, ix.severity * 4), color },
      hoverinfo: 'none' as const, showlegend: false,
    };
  });

  const nodeTrace = {
    type: 'scatter' as const, mode: 'markers+text' as const,
    x: positions.map((p) => p.x), y: positions.map((p) => p.y),
    text: nodes, textposition: 'top center' as const,
    textfont: { size: 10, color: '#f0f4ff' },
    marker: { size: 14, color: '#00d4ff', line: { width: 2, color: '#001a2e' } },
    hovertext: nodes, hoverinfo: 'text' as const, showlegend: false,
  };

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <Plot
        data={[...edgeTraces, nodeTrace] as any}
        layout={{
          paper_bgcolor: 'rgba(6,13,26,1)', plot_bgcolor: 'rgba(6,13,26,1)',
          font: { color: '#f0f4ff', family: 'Inter' },
          height: 480, margin: { l: 20, r: 20, t: 40, b: 20 },
          title: { text: `Drug Interaction Network (${interactions.length} edges)`, font: { size: 14, color: '#8899bb' } },
          xaxis: { showgrid: false, zeroline: false, showticklabels: false },
          yaxis: { showgrid: false, zeroline: false, showticklabels: false },
          showlegend: false,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />
    </div>
  );
}

function PatientPathPlot({ path, patientId }: { path: { nodes: { id: string; label: string; type: string }[]; edges: { from: string; to: string; label: string; severity?: number }[] }; patientId: string }) {
  const TYPE_COLORS: Record<string, string> = {
    Patient: '#00d4ff', Drug: '#ffa502', Condition: '#2ed573', Provider: '#a29bfe', Procedure: '#ff7675', ClinicalFinding: '#fdcb6e'
  };
  const TYPE_SYMBOLS: Record<string, string> = {
    Patient: 'circle', Drug: 'diamond', Condition: 'square', Provider: 'star', Procedure: 'cross', ClinicalFinding: 'triangle-up'
  };

  const positions: Record<string, [number, number]> = {};
  const byType: Record<string, typeof path.nodes> = {};
  path.nodes.forEach((n) => {
    if (n.type === 'Patient') positions[n.id] = [0, 0];
    else (byType[n.type] = byType[n.type] || []).push(n);
  });

  const arcAngles: Record<string, number> = { Drug: 0, Condition: 72, Provider: 144, Procedure: 216, ClinicalFinding: 288 };
  Object.entries(byType).forEach(([type, group]) => {
    const center = ((arcAngles[type] ?? 60) * Math.PI) / 180;
    const spread = (70 * Math.PI) / 180;
    group.forEach((n, i) => {
      const a = group.length === 1 ? center : center - spread / 2 + (i * spread) / (group.length - 1);
      positions[n.id] = [3 * Math.cos(a), 3 * Math.sin(a)];
    });
  });

  const edgeTraces = path.edges.map((e) => {
    const [x0, y0] = positions[e.from] ?? [0, 0];
    const [x1, y1] = positions[e.to] ?? [0, 0];
    const color = e.severity && e.severity >= 0.7 ? '#ff4757' : '#4a5980';
    return {
      type: 'scatter' as const, mode: 'lines' as const,
      x: [x0, x1, null], y: [y0, y1, null],
      line: { width: e.severity && e.severity >= 0.7 ? 3 : 1.5, color },
      hoverinfo: 'none' as const, showlegend: false,
    };
  });

  const nodeTraces = Object.entries(TYPE_COLORS).map(([type, color]) => {
    const ns = path.nodes.filter((n) => n.type === type);
    if (!ns.length) return null;
    return {
      type: 'scatter' as const, mode: 'markers+text' as const,
      x: ns.map((n) => (positions[n.id] ?? [0, 0])[0]),
      y: ns.map((n) => (positions[n.id] ?? [0, 0])[1]),
      text: ns.map((n) => n.label), textposition: 'top center' as const,
      textfont: { size: 10, color: '#f0f4ff' },
      marker: { size: type === 'Patient' ? 22 : 16, color, symbol: TYPE_SYMBOLS[type], line: { width: 2, color: '#001a2e' } },
      name: type, hovertext: ns.map((n) => `${n.type}: ${n.label}`), hoverinfo: 'text' as const,
    };
  }).filter(Boolean);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <Plot
        data={[...edgeTraces, ...nodeTraces] as any}
        layout={{
          paper_bgcolor: 'rgba(6,13,26,1)', plot_bgcolor: 'rgba(6,13,26,1)',
          font: { color: '#f0f4ff', family: 'Inter' }, height: 520,
          title: { text: `Relationship Path — ${patientId}`, font: { size: 14, color: '#8899bb' } },
          margin: { l: 20, r: 20, t: 50, b: 20 },
          xaxis: { showgrid: false, zeroline: false, showticklabels: false },
          yaxis: { showgrid: false, zeroline: false, showticklabels: false },
          legend: { orientation: 'h', y: 1.05 },
          showlegend: true,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  chainRow: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '12px 14px', background: 'var(--bg-glass)',
    border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)',
    flexWrap: 'wrap',
  },
};
