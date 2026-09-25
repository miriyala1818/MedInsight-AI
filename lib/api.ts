import type { ApiError, AppConfig, EvaluationDashboard, QueryResponse, ConversationListResponse, ConversationDetail } from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';
const API_PREFIX = '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers
    },
    cache: 'no-store'
  });

  if (!response.ok) {
    let payload: ApiError | undefined;
    try {
      payload = (await response.json()) as ApiError;
    } catch {
      payload = undefined;
    }

    const message = payload?.error?.message ?? `Request failed (${response.status})`;
    const code = payload?.error?.code ?? 'request_failed';
    const error = new Error(message) as Error & { code?: string; status?: number };
    error.code = code;
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return {} as T;
  }

  const text = await response.text();
  return (text ? JSON.parse(text) : {}) as T;
}

export function getAppConfig() {
  return request<AppConfig>('/config');
}

export function submitQuery(question: string, sessionId?: string, conversationId?: string) {
  return request<QueryResponse>('/query', {
    method: 'POST',
    body: JSON.stringify({ question, session_id: sessionId ?? null, conversation_id: conversationId ?? null })
  });
}

export function getEvaluationDashboard() {
  return request<EvaluationDashboard>('/dashboard');
}

export function getHealth() {
  return request<{ status: string; app_name: string; environment: string; version: string }>('/health');
}

export async function listConversations(limit = 50, offset = 0): Promise<ConversationListResponse> {
  return request<ConversationListResponse>(`/conversations?limit=${limit}&offset=${offset}`);
}

export async function createConversation(title?: string): Promise<ConversationDetail> {
  return request<ConversationDetail>('/conversations', {
    method: 'POST',
    body: JSON.stringify(title ? { title } : {}),
  });
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${id}`);
}

export async function deleteConversation(id: string): Promise<void> {
  await request<void>(`/conversations/${id}`, { method: 'DELETE' });
}

export async function updateConversation(id: string, title: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}
