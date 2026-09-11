"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";
import StatusBadge from "@/components/StatusBadge";

const MODES = ["alert_only", "paper", "live_auto"];

export default function Strategies() {
  const { data, refresh } = usePoll(() => api.strategies(), 10000);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function setMode(name: string, mode: string) {
    setBusy(name + mode); setMsg(null);
    try {
      await api.setMode(name, mode);
      setMsg(`✓ ${name} → ${mode}`);
      refresh();
    } catch (e: any) { setMsg(`✗ ${e.message}`); }
    finally { setBusy(null); }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Strategies</h1>
      <p className="text-sm text-terminal-dim font-mono">
        Status badges are derived server-side from gate evidence — the UI only renders them. Live Auto stays locked until both gates pass.
      </p>
      {msg && <div className="card font-mono text-sm">{msg}</div>}
      {(data?.strategies || []).map((s: any) => (
        <div key={s.name} className="card space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <div className="font-bold font-mono">{s.name}</div>
              <div className="text-xs text-terminal-dim font-mono">{s.symbol} {s.timeframe} · mode: <b>{s.mode}</b> · live trades: {s.live_trades}</div>
            </div>
            <StatusBadge status={s.status} />
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <div className="bg-terminal-bg rounded p-3">
              <div className="text-xs uppercase text-terminal-dim mb-1">Backtest gate {s.backtest_gate?.passed ? "✓" : "✗"}</div>
              {s.backtest_gate ? (
                <ul className="font-mono text-xs space-y-1">
                  {Object.entries(s.backtest_gate.checks || {}).map(([k, v]) => (
                    <li key={k} className={v ? "text-terminal-up" : "text-terminal-down"}>{v ? "✓" : "✗"} {k}</li>
                  ))}
                  <li className="text-terminal-dim">metrics: {JSON.stringify(s.backtest_gate.metrics)}</li>
                </ul>
              ) : <p className="font-mono text-xs text-terminal-dim">No backtest report yet — run one from the Backtest page.</p>}
            </div>
            <div className="bg-terminal-bg rounded p-3">
              <div className="text-xs uppercase text-terminal-dim mb-1">Paper gate {s.paper_gate?.passed ? "✓" : "✗"}</div>
              {s.paper_gate ? (
                <ul className="font-mono text-xs space-y-1">
                  {Object.entries(s.paper_gate.checks || {}).map(([k, v]) => (
                    <li key={k} className={v ? "text-terminal-up" : "text-terminal-down"}>{v ? "✓" : "✗"} {k}</li>
                  ))}
                  <li className="text-terminal-dim">paper: {s.paper_metrics?.trade_count || 0} trades · exp R {s.paper_metrics?.expectancy_r ?? "—"}</li>
                </ul>
              ) : <p className="font-mono text-xs text-terminal-dim">No paper trades yet — switch to paper mode and trade from Live Terminal.</p>}
            </div>
          </div>

          <div>
            <div className="text-xs uppercase text-terminal-dim mb-1">Execution mode</div>
            <div className="flex gap-2 flex-wrap">
              {MODES.map((m) => {
                const locked = m === "live_auto" && !s.live_auto_allowed;
                return (
                  <button
                    key={m}
                    disabled={busy !== null || s.mode === m || locked}
                    onClick={() => setMode(s.name, m)}
                    title={locked ? s.gate_reasons?.join("; ") : ""}
                    className={`${s.mode === m ? "btn-primary" : "btn"} ${locked ? "opacity-40" : ""}`}
                  >
                    {locked ? "🔒 " : ""}{m}
                  </button>
                );
              })}
            </div>
            <ul className="font-mono text-xs text-terminal-dim mt-2 space-y-0.5">
              {(s.gate_reasons || []).map((r: string, i: number) => <li key={i}>• {r}</li>)}
            </ul>
          </div>
        </div>
      ))}
    </div>
  );
}
