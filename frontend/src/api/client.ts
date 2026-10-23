import axios from 'axios';
import type { LocationInfo, TripAnalysisRequest, TripAnalysisResponse } from '../types/api';

export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem('SPOTTER_API_BASE_URL');
    if (custom && custom.trim()) {
      return custom.trim().replace(/\/+$/, '');
    }
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return 'http://127.0.0.1:8000/api';
}

export function setApiBaseUrl(url: string): void {
  if (typeof window !== 'undefined') {
    if (url && url.trim()) {
      localStorage.setItem('SPOTTER_API_BASE_URL', url.trim().replace(/\/+$/, ''));
    } else {
      localStorage.removeItem('SPOTTER_API_BASE_URL');
    }
  }
}

export const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Dynamically use current active baseURL
apiClient.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl();
  return config;
});

export async function analyzeTrip(req: TripAnalysisRequest): Promise<TripAnalysisResponse> {
  const resp = await apiClient.post<TripAnalysisResponse>('/routes/analyze/', req);
  return resp.data;
}

export async function fetchLocationSuggestions(query: string): Promise<LocationInfo[]> {
  if (!query || query.trim().length < 2) return [];
  try {
    const resp = await apiClient.get<LocationInfo[]>('/geocode/', {
      params: { q: query.trim() },
    });
    return resp.data;
  } catch (err) {
    console.error('Geocoding autocomplete failed:', err);
    return [];
  }
}

export async function checkSystemHealth(): Promise<boolean> {
  try {
    const resp = await apiClient.get('/health/');
    return resp.status === 200 && resp.data?.status === 'healthy';
  } catch {
    return false;
  }
}
