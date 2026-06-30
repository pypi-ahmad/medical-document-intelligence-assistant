export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
}

export interface AuthPayload {
  user: {
    id: string;
    email: string;
    full_name: string;
    is_admin: boolean;
    created_at: string;
  };
  tokens: AuthTokens;
}

export interface DocumentItem {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  page_count: number | null;
  status: string;
  created_at: string;
}

export interface Citation {
  document_id: string;
  document_name: string;
  page_number: number | null;
  chunk_id: string | null;
  evidence_text: string;
}

export interface OCRPage {
  page_number: number;
  text: string;
  confidence: number | null;
  layout_json: Record<string, unknown>;
  provider: string;
}

export interface QAResult {
  session_id: string;
  answer: string;
  extracted_information: string;
  educational_background: string;
  citations: Citation[];
  safety: {
    disclaimer: string;
  };
  model: string;
}

export interface QAStreamDone {
  session_id: string;
  answer: string;
  citations: Citation[];
  model: string;
  safety: {
    disclaimer: string;
  };
}

export interface QAStreamHandlers {
  onSession?: (payload: { session_id: string; model: string }) => void;
  onToken?: (token: string) => void;
  onDone?: (payload: QAStreamDone) => void;
  onError?: (message: string) => void;
}

export interface TimelineEvent {
  id: number;
  document_id: string;
  event_type: string;
  event_date: string | null;
  title: string;
  description: string | null;
  metadata: Record<string, unknown>;
  page_number: number | null;
}

const API_BASE = "/api";

const TOKEN_KEY = "mdia_access_token";
const REFRESH_TOKEN_KEY = "mdia_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setTokens(tokens: AuthTokens): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return null;

  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    return null;
  }

  const payload = (await response.json()) as AuthTokens;
  setTokens(payload);
  return payload.access_token;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const execute = async (token: string | null): Promise<Response> => {
    const headers = new Headers(init?.headers ?? {});
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    if (!headers.has("Content-Type") && !(init?.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    return fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
    });
  };

  let token = getAccessToken();
  let response = await execute(token);

  if (response.status === 401) {
    token = await refreshAccessToken();
    if (token) {
      response = await execute(token);
    }
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function bootstrapAdmin(payload: {
  email: string;
  full_name: string;
  password: string;
}): Promise<AuthPayload> {
  const result = await request<AuthPayload>("/auth/bootstrap", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setTokens(result.tokens);
  return result;
}

export async function login(payload: { email: string; password: string }): Promise<AuthPayload> {
  const result = await request<AuthPayload>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setTokens(result.tokens);
  return result;
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append("file", file);
  return request<DocumentItem>("/documents/", {
    method: "POST",
    body: formData,
  });
}

export function listDocuments(): Promise<DocumentItem[]> {
  return request<DocumentItem[]>("/documents/");
}

export function processDocument(documentId: string): Promise<any> {
  return request<any>(`/medical/process/${documentId}`, { method: "POST" });
}

export function getOCRPages(documentId: string): Promise<OCRPage[]> {
  return request<OCRPage[]>(`/medical/documents/${documentId}/ocr`);
}

export function getEntities(documentId: string): Promise<any[]> {
  return request<any[]>(`/medical/documents/${documentId}/entities`);
}

export function getLabs(documentId: string): Promise<any[]> {
  return request<any[]>(`/medical/documents/${documentId}/labs`);
}

export function getMedications(documentId: string): Promise<any[]> {
  return request<any[]>(`/medical/documents/${documentId}/medications`);
}

export function search(
  query: string,
  documentIds: string[] = [],
  options?: {
    startDate?: string;
    endDate?: string;
    filters?: Record<string, unknown>;
    topK?: number;
  },
): Promise<any> {
  return request<any>("/search", {
    method: "POST",
    body: JSON.stringify({
      query,
      document_ids: documentIds,
      top_k: options?.topK ?? 10,
      start_date: options?.startDate || null,
      end_date: options?.endDate || null,
      filters: options?.filters ?? {},
    }),
  });
}

export function askQuestion(question: string, sessionId?: string, documentIds: string[] = []): Promise<QAResult> {
  return request<QAResult>("/qa/query", {
    method: "POST",
    body: JSON.stringify({ question, session_id: sessionId, document_ids: documentIds, top_k: 10 }),
  });
}

export async function streamQuestion(
  question: string,
  sessionId?: string,
  documentIds: string[] = [],
  handlers: QAStreamHandlers = {},
): Promise<QAStreamDone> {
  const execute = async (token: string | null): Promise<Response> => {
    const headers = new Headers({ "Content-Type": "application/json" });
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return fetch(`${API_BASE}/qa/query/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        question,
        session_id: sessionId,
        document_ids: documentIds,
        top_k: 10,
      }),
    });
  };

  let token = getAccessToken();
  let response = await execute(token);
  if (response.status === 401) {
    token = await refreshAccessToken();
    if (token) {
      response = await execute(token);
    }
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Streaming request failed: ${response.status}`);
  }
  if (!response.body) {
    throw new Error("Streaming response body is missing.");
  }

  const decoder = new TextDecoder("utf-8");
  const reader = response.body.getReader();
  let buffer = "";
  let donePayload: QAStreamDone | null = null;

  const flushEvent = (rawEvent: string): void => {
    const lines = rawEvent.split("\n");
    let eventType = "message";
    const dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventType = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice("data:".length).trim());
      }
    }
    if (!dataLines.length) return;
    const jsonData = dataLines.join("\n");
    let payload: any;
    try {
      payload = JSON.parse(jsonData);
    } catch {
      handlers.onError?.("Failed to parse streaming payload.");
      return;
    }

    if (eventType === "session") {
      handlers.onSession?.(payload);
      return;
    }
    if (eventType === "token") {
      handlers.onToken?.(String(payload.text ?? ""));
      return;
    }
    if (eventType === "done") {
      donePayload = payload as QAStreamDone;
      handlers.onDone?.(donePayload);
      return;
    }
    if (eventType === "error") {
      handlers.onError?.(String(payload.error ?? "Unknown streaming error."));
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      if (rawEvent.trim()) {
        flushEvent(rawEvent);
      }
      boundary = buffer.indexOf("\n\n");
    }
  }

  if (!donePayload) {
    throw new Error("Streaming ended before final payload.");
  }
  return donePayload;
}

export function summarize(documentIds: string[], summaryType: string, length: string): Promise<any> {
  return request<any>("/summaries", {
    method: "POST",
    body: JSON.stringify({ document_ids: documentIds, summary_type: summaryType, length }),
  });
}

export function timeline(
  documentIds: string[],
  eventTypes: string[] = [],
  options?: { startDate?: string; endDate?: string },
): Promise<{ events: TimelineEvent[] }> {
  return request<{ events: TimelineEvent[] }>("/timelines", {
    method: "POST",
    body: JSON.stringify({
      document_ids: documentIds,
      event_types: eventTypes,
      start_date: options?.startDate || null,
      end_date: options?.endDate || null,
    }),
  });
}

export function generateReport(documentIds: string[], title: string): Promise<any> {
  return request<any>("/reports/generate", {
    method: "POST",
    body: JSON.stringify({ document_ids: documentIds, title }),
  });
}

export function listMemory(): Promise<any[]> {
  return request<any[]>("/memory");
}

export function createMemory(payload: {
  memory_type: string;
  memory_key: string;
  memory_value: Record<string, unknown>;
  ttl_days?: number;
}): Promise<any> {
  return request<any>("/memory", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function clearMemory(memoryType?: string): Promise<{ deleted: number }> {
  const query = memoryType ? `?memory_type=${encodeURIComponent(memoryType)}` : "";
  return request<{ deleted: number }>(`/memory${query}`, { method: "DELETE" });
}

export function listAgentRuns(): Promise<any[]> {
  return request<any[]>("/agents/runs");
}

export function getModelConfig(): Promise<any> {
  return request<any>("/models/config");
}

export function updateModelConfig(payload: Record<string, unknown>): Promise<any> {
  return request<any>("/models/config", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getSystemHealth(): Promise<any> {
  return request<any>("/system/health");
}
