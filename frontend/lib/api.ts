// All calls are same-origin relative URLs — Next.js rewrites /api/* to FastAPI.
// Browser code never touches localhost directly (preview-safe).
async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
  });
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try {
      const j = await r.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || j);
    } catch {}
    throw new Error(detail);
  }
  return (await r.json()) as T;
}

export const api = {
  health: () => req<any>("/api/health"),
  analysis: (symbol: string, timeframe: string, ai = false) =>
    req<any>(`/api/market/analysis?symbol=${symbol}&timeframe=${timeframe}&count=300&ai=${ai}`),
  tick: (symbol: string) => req<any>(`/api/market/tick?symbol=${symbol}`),
  strategies: () => req<{ strategies: any[] }>("/api/strategies"),
  strategy: (name: string) => req<any>(`/api/strategies/${name}`),
  setMode: (name: string, mode: string) =>
    req<any>(`/api/strategies/${name}/mode`, { method: "POST", body: JSON.stringify({ mode }) }),
  riskStatus: () => req<any>("/api/risk/status"),
  riskEvaluate: (body: any) => req<any>("/api/risk/evaluate", { method: "POST", body: JSON.stringify(body) }),
  execute: (body: any) => req<any>("/api/execution/signal", { method: "POST", body: JSON.stringify(body) }),
  paper: () => req<any>("/api/execution/paper"),
  backtestRun: (body: any) => req<any>("/api/backtest/run", { method: "POST", body: JSON.stringify(body) }),
  backtestReports: () => req<any>("/api/backtest/reports"),
  backtestReport: (id: string) => req<any>(`/api/backtest/reports/${id}`),
  journal: (kind?: string) => req<any>(`/api/journal${kind ? `?kind=${kind}` : ""}`),
  knowledge: () => req<any>("/api/knowledge"),
  addSource: (body: any) => req<any>("/api/knowledge", { method: "POST", body: JSON.stringify(body) }),
  deleteSource: (id: string) => req<any>(`/api/knowledge/${id}`, { method: "DELETE" }),
  searchKb: (q: string) => req<any>(`/api/knowledge/search?q=${encodeURIComponent(q)}`),
};
