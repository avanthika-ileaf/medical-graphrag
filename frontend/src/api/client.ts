// src/api/client.ts
import axios from 'axios';

const client = axios.create({
  baseURL: 'http://localhost:5173/api',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Unknown error';
    return Promise.reject(new Error(msg));
  }
);

export default client;
