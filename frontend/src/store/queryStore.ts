// src/store/queryStore.ts
import { create } from 'zustand';
import type { QueryHistoryItem, CompareQueryResponse } from '../types';

interface QueryStore {
  currentQuery: string;
  setCurrentQuery: (q: string) => void;

  isLoading: boolean;
  setIsLoading: (v: boolean) => void;

  lastResult: CompareQueryResponse | null;
  setLastResult: (r: CompareQueryResponse | null) => void;

  history: QueryHistoryItem[];
  addToHistory: (item: QueryHistoryItem) => void;
  clearHistory: () => void;

  activeTab: string;
  setActiveTab: (tab: string) => void;

  severityFilter: number;
  setSeverityFilter: (v: number) => void;
}

export const useQueryStore = create<QueryStore>((set) => ({
  currentQuery: '',
  setCurrentQuery: (q) => set({ currentQuery: q }),

  isLoading: false,
  setIsLoading: (v) => set({ isLoading: v }),

  lastResult: null,
  setLastResult: (r) => set({ lastResult: r }),

  history: [],
  addToHistory: (item) =>
    set((s) => ({ history: [item, ...s.history].slice(0, 20) })),
  clearHistory: () => set({ history: [] }),

  activeTab: 'compare',
  setActiveTab: (tab) => set({ activeTab: tab }),

  severityFilter: 0.6,
  setSeverityFilter: (v) => set({ severityFilter: v }),
}));
