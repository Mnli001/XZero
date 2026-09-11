"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";
import StatCard from "@/components/StatCard";

export default function Risk() {
  const { data, refresh } = usePoll(() => api.riskStatus(), 5000);
  const [form, setForm] = useState({ balance: "10000", entry: "1.0850", stop_loss: "1.0800", risk_pct: "2", tick_value: "1", tick_size: "0.0001", current_spread: "1.2" });
  const [result, setResult] = useState<any>(null);

  function set(k: string, v: string) { setForm({ ...form, [k]: v }); }

  async function evaluate() {
    const r = await api.riskEvaluate({
      balance: parseFloat(form.balance), entry: parseFloat(form.entry), stop_loss: parseFloat(form.stop_loss),
      risk_pct: parseFloat(form.risk_pct), tick_value: parseFloat(form.tick_value), tick_size: parseFloat(form.tick_size),
      current_spread: parseFloat(form.current_spread), recent_spreads: Array(50).fill(1.2),
    });
    setResult(r);
  }

  const c = data?.circuit;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Risk Dashboard</h1>
      <p className="text-sm text-terminal-dim font-mono">All limits enforced server-side — this page inspects, never overrides.</p>

      <div className="grid md:grid-cols-4 gap-4">
        <StatCard label="Circuit breaker" value={c?.locked ? "LOCKED" : "OK"} sub={c?.locked ? `until ${c?.locked_until}` : `${c?.consecutive_losses || 0}/${c?.max_consecutive_losses} losses`} tone={c?.locked ? "down" : "up"} />
        <StatCard label="Risk cap" value={`${data?.caps?.default_risk_pct}% / max ${data?.caps?.max_risk_pct}%`} sub={`hard ceiling ${data?.caps?.hard_ceiling}%`} />
        <StatCard label="Daily loss limit" value={`${data?.guards?.daily_loss_limit_pct}%`} sub="blocks new trades beyond" />
        <StatCard label="Exposure" value={`≤${data?.guards?.max_open_positions} pos`} sub={`rollover blackout ${data?.guards?.rollover_blackout_utc?.join("–")} UTC`} />
      </div>

      <div className="card space-y-3">
        <h2 className="font-bold">Pre-trade evaluation (binding logic, dry-run)</h2>
        <div className="grid md:grid-cols-4 gap-3">
          {Object.entries({ balance: "Balance", entry: "Entry", stop_loss: "Stop loss", risk_pct: "Risk %" }).map(([k, label]) => (
            <label key={k} className="text-xs font-mono text-terminal-dim">{label}
              <input value={(form as any)[k]} onChange={(e) => set(k, e.target.value)} className="mt-1" />
            </label>
          ))}
        </div>
        <button className="btn-primary" onClick={evaluate}>Evaluate</button>
        {result && (
          <div className={`rounded p-3 font-mono text-sm ${result.allowed ? "bg-terminal-up/10" : "bg-terminal-down/10"}`}>
            <div className="font-bold">{result.allowed ? `✓ ALLOWED — ${result.lots} lots, risk $${result.risk_amount}` : "✗ BLOCKED"}</div>
            <ul className="mt-1 space-y-0.5 text-xs">
              {result.reasons.map((r: string, i: number) => <li key={i}>• {r}</li>)}
            </ul>
            {(result.details?.sizing_notes || []).map((n: string, i: number) => <div key={i} className="text-xs text-terminal-accent">• {n}</div>)}
          </div>
        )}
      </div>
    </div>
  );
}
