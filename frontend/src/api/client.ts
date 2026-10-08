import type { HealthStatus } from '../types/health';

export const REQUEST_ID_HEADER = 'X-Request-ID';

export class ApiError extends Error {
  public status: number;
  public code: string;
  public details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function buildHeaders(token?: string, requestId: string = crypto.randomUUID()): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    [REQUEST_ID_HEADER]: requestId,
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function request<T>(
  url: string,
  options: {
    method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
    token?: string;
    body?: unknown;
    requestId?: string;
  } = {},
  fetchImpl: typeof fetch = fetch,
): Promise<T> {
  const { method = 'GET', token, body, requestId } = options;
  const headers = buildHeaders(token, requestId);

  const init: RequestInit = {
    method,
    headers,
  };

  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }

  const response = await fetchImpl(url, init);

  if (!response.ok) {
    let errorCode = 'UNKNOWN_ERROR';
    let errorMessage = `HTTP ${response.status} ${response.statusText}`;
    let details: Record<string, unknown> = {};

    try {
      const errData = await response.json();
      if (errData?.error) {
        errorCode = errData.error.code || errorCode;
        errorMessage = errData.error.message || errorMessage;
        details = errData.error.details || {};
      } else if (errData?.detail) {
        errorMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // Body not JSON
    }

    throw new ApiError(response.status, errorCode, errorMessage, details);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export async function fetchHealth(fetchImpl: typeof fetch = fetch): Promise<HealthStatus> {
  const response = await fetchImpl('/health', { headers: buildHeaders() });
  if (response.status !== 200 && response.status !== 503) {
    throw new Error(`Unexpected health status ${response.status}`);
  }
  return (await response.json()) as HealthStatus;
}
