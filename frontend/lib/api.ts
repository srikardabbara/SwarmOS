/**
 * API client for SwarmOS backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

export const api = {
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

    const response = await fetch(`${API_BASE_URL}/traces?${query}`);
    if (!response.ok) throw new Error('Failed to fetch traces');
    return response.json();
  },

  async getTrace(id: string): Promise<Trace> {
    const response = await fetch(`${API_BASE_URL}/traces/${id}`);
    if (!response.ok) throw new Error('Failed to fetch trace');
    return response.json();
  },

  async deleteTrace(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/traces/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete trace');
  },

  async health(): Promise<{ status: string; timestamp: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) throw new Error('Backend unhealthy');
    return response.json();
  },
};
