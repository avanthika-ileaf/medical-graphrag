// src/api/query.ts
import client from './client';
import type { QueryResponse, CompareQueryResponse } from '../types';

export const runQuery = async (query: string): Promise<QueryResponse> => {
  const { data } = await client.post<QueryResponse>('/query/simple', { query });
  return data;
};

export const runAgentQuery = async (query: string): Promise<QueryResponse> => {
  const { data } = await client.post<QueryResponse>('/query', { query });
  return data;
};

export const compareQuery = async (query: string): Promise<CompareQueryResponse> => {
  const { data } = await client.post<CompareQueryResponse>('/query/compare', { query });
  return data;
};

export const getPresets = async (): Promise<string[]> => {
  const { data } = await client.get<{ presets: string[] }>('/query/presets');
  return data.presets;
};
