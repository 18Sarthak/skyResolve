// In production (Vercel), set VITE_API_URL to your Render backend URL.
// In local dev, the Vite proxy forwards /api → http://localhost:8000
export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

export interface MessageResponse {
  response: string;
  actions_taken: string[];
  escalated: boolean;
  escalation_reason: string | null;
}

export interface HistoryTurn {
  id: number;
  pnr: string;
  timestamp: string;
  customer_message: string;
  agent_response: string;
  actions_taken_json: string[];
  escalated: boolean;
  escalation_reason: string | null;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface HealthResponse {
  status: "ok" | string;
  openai_key_configured: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    throw new Error(`SkyResolve backend returned ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function sendMessage(pnr: string, message: string) {
  return request<MessageResponse>(`/conversation/${encodeURIComponent(pnr)}/message`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function getHistory(pnr: string) {
  return request<HistoryTurn[]>(`/conversation/${encodeURIComponent(pnr)}/history`);
}

export function getHealth() {
  return request<HealthResponse>("/health");
}
