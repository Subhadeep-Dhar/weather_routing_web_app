import axios from 'axios';
import type { LocationInfo, TripAnalysisRequest, TripAnalysisResponse } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
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
