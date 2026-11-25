/**
 * API client for SwarmOS backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const KEY_STORAGE = 'swarmos_project_key';

export interface TraceEvent {
  id: string;
  trace_id: string;
  timestamp: string;
  event_type: string;
  agent: string | null;
  data: Record<string, any>;
  parent_event_id: string | null;
}

export interface ValidationResult {
  id: string;
  trace_id: string;
  validation_type: string;
  passed: boolean;
  message: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface Trace {
  id: string;
  test_id: string | null;
  workflow_id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  input_data: Record<string, any>;
  output_data: Record<string, any> | null;
  metadata: Record<string, any>;
  events?: TraceEvent[];
  validation_results?: ValidationResult[];
}

export interface Project {
  id: string;
  name: string;
  api_key?: string;
}

export class ProjectKeyError extends Error {
  constructor(message = 'Project key was rejected') {
    super(message);
    this.name = 'ProjectKeyError';
  }
}

export function getProjectKey(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(KEY_STORAGE);
}

export function setProjectKey(key: string) {
  localStorage.setItem(KEY_STORAGE, key);
}

export function clearProjectKey() {
  localStorage.removeItem(KEY_STORAGE);
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const key = getProjectKey();
  if (key) headers.set('Authorization', `Bearer ${key}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401) {
    clearProjectKey();
    throw new ProjectKeyError();
  }
  return response;
}

export const api = {
  async createProject(name: string): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || 'Failed to create project');
    }
    return response.json();
  },

  async confirmProjectKey(key: string): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/projects/current`, {
      headers: { Authorization: `Bearer ${key}` },
    });
    if (!response.ok) throw new Error('That project key was not recognized');
    return response.json();
  },

  async listTraces(params?: {
    workflow_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<Trace[]> {
    const query = new URLSearchParams();
    if (params?.workflow_id) query.set('workflow_id', params.workflow_id);
    if (params?.status) query.set('status', params.status);
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());

    const response = await request(`/traces?${query}`);
    if (!response.ok) throw new Error('Failed to fetch traces');
    return response.json();
  },

  async getTrace(id: string): Promise<Trace> {
    const response = await request(`/traces/${id}`);
    if (!response.ok) throw new Error('Failed to fetch trace');
    return response.json();
  },

  async deleteTrace(id: string): Promise<void> {
    const response = await request(`/traces/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete trace');
  },

  async importLangSmith(apiKey: string, url: string): Promise<Trace> {
    const response = await request('/langsmith/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey, url }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || 'Could not read that LangSmith trace');
    }
    return response.json();
  },

  async health(): Promise<{ status: string; timestamp: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) throw new Error('Backend unhealthy');
    return response.json();
  },
};
