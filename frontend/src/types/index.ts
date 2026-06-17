// src/types/index.ts
// Shared TypeScript types mirroring the FastAPI Pydantic schemas

export interface ArxivPaper {
  arxiv_id: string;
  title: string;
  authors: string[];
  summary: string;
  published: string;
  url: string;
  topics: string[];
  source: string;
  score?: number;
}

export interface ProvenanceInfo {
  graph_only: string[];
  vector_only: string[];
  confirmed: string[];
}

export interface QueryResponse {
  query: string;
  answer: string;
  confidence: number;
  provenance: ProvenanceInfo;
  graph_hits: Record<string, unknown>[];
  vector_hits: Record<string, unknown>[];
  arxiv_papers: ArxivPaper[];
  agent_output?: string;
  latency_ms: number;
  model: string;
}

export interface StandardRAGResult {
  answer: string;
  confidence: number;
  latency_ms: number;
  sources: string;
}

export interface GraphRAGResult {
  answer: string;
  confidence: number;
  latency_ms: number;
  provenance: ProvenanceInfo;
  agent_output?: string;
}

export interface CompareQueryResponse {
  query: string;
  standard_rag: StandardRAGResult;
  graph_rag: GraphRAGResult;
  graph_hits: Record<string, unknown>[];
  arxiv_papers: ArxivPaper[];
}

export interface DrugInteraction {
  drug1: string;
  drug2: string;
  severity: number;
  mechanism: string;
}

export interface PatientSummary {
  patientID: string;
  name: string;
  age?: number;
  gender?: string;
  drugCount?: number;
  conditions: string[];
  drugs: string[];
  interactions: DrugInteraction[];
  risk_level: 'low' | 'medium' | 'high';
}

export interface DrugInfo {
  name: string;
  dosage?: string;
  frequency?: string;
}

export interface ConditionInfo {
  name: string;
  severity?: number;
  since?: string;
}

export interface PatientProfile {
  patientID: string;
  name: string;
  age?: number;
  gender?: string;
  drugs: DrugInfo[];
  conditions: ConditionInfo[];
  providers: string[];
  interactions: DrugInteraction[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'Patient' | 'Drug' | 'Condition' | 'Provider';
}

export interface GraphEdge {
  from: string;
  to: string;
  label: string;
  severity?: number;
}

export interface PatientGraphPath {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphStatistics {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

export interface DrugInteractionEdge {
  drug1: string;
  drug2: string;
  severity: number;
  mechanism: string;
}

export interface KHopChain {
  chain: string[];
  hops: number;
  severities: number[];
}

export interface QueryHistoryItem {
  id: string;
  query: string;
  timestamp: Date;
  answer: string;
  confidence: number;
  latency_ms: number;
}
