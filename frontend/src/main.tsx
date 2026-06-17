// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
if (typeof window !== 'undefined') {
  (window as any).global = window;
}
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
