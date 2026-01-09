import axios from 'axios';

// Use relative path for production, fallback to local for development
const API_BASE = (import.meta.env.PROD) ? '/cryptotrader/api' : 'http://localhost:8006/api';

export const api = {
    getStatus: () => axios.get(`${API_BASE}/status`),
    getHistory: () => axios.get(`${API_BASE}/history`),
    startTrading: () => axios.post(`${API_BASE}/start`),
    stopTrading: () => axios.post(`${API_BASE}/stop`),
    updateConfig: (config) => axios.post(`${API_BASE}/config`, config),
};
