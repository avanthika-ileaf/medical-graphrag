// src/api/patients.ts
import client from './client';
import type { PatientSummary, PatientProfile, PatientGraphPath } from '../types';

export const listPatients = async (filter = 'high-risk', limit = 30): Promise<PatientSummary[]> => {
  const { data } = await client.get<PatientSummary[]>('/patients', { params: { filter, limit } });
  return data;
};

export const getHighRiskPatients = async (limit = 30): Promise<PatientSummary[]> => {
  const { data } = await client.get<PatientSummary[]>('/patients/high-risk', { params: { limit } });
  return data;
};

export const getContraindicatedPatients = async (limit = 30): Promise<PatientSummary[]> => {
  const { data } = await client.get<PatientSummary[]>('/patients/contraindicated', { params: { limit } });
  return data;
};

export const getPatientProfile = async (id: string): Promise<PatientProfile> => {
  const { data } = await client.get<PatientProfile>(`/patients/${id}`);
  return data;
};

export const getPatientGraphPath = async (id: string): Promise<PatientGraphPath> => {
  const { data } = await client.get<PatientGraphPath>(`/graph/patient/${id}/path`);
  return data;
};
