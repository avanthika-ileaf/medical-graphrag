// src/api/stats.ts
import client from './client';
import type { GraphStatistics, DrugInteractionEdge, KHopChain } from '../types';

export const getGraphStats = async (): Promise<GraphStatistics> => {
  const { data } = await client.get<GraphStatistics>('/stats');
  return data;
};

export const getDrugInteractions = async (minSeverity = 0.6): Promise<DrugInteractionEdge[]> => {
  const { data } = await client.get<DrugInteractionEdge[]>('/graph/drug-interactions', {
    params: { min_severity: minSeverity },
  });
  return data;
};

export const getKHopChain = async (drug: string, k = 2): Promise<KHopChain[]> => {
  const { data } = await client.get<KHopChain[]>('/graph/khop', { params: { drug, k } });
  return data;
};

export const searchArxiv = async (q: string) => {
  const { data } = await client.get('/arxiv/search', { params: { q } });
  return data;
};
