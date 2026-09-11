"use client";
import Link from "next/link";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";
import StatCard from "@/components/StatCard";
import StatusBadge from "@/components/StatusBadge";
import Checklist from "@/components/Checklist";
import ConfidenceBar from "@/components/ConfidenceBar";

export default function Overview() {
  const health = usePoll(() => api.health(), 10000);
  const strategies = usePoll(() => api.strategies(), 15000);
  const analysis = usePoll(() => api.analysis("EURUSD", "M5", false), 15000);

  const h = health.data;
  const locked = h?.circuit?.locked;
  const rows = strategies.data?.strategies || [];
  const a = analysis.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold">Overview</h1>
        <div className="flex gap-2 font-mono text-xs">
          <span className={`px-2 py-1 rounded border ${h?.mt5_mode === "live" ? "border-terminal-up text-terminal-up" : "border-terminal-accent text-terminal-accent"}`}>
            MT5: {h?.mt5_mode || "…"} {h?.mt5_connected ? "●" : "○"}
          </span>
          <span className={`px-2 py-1 rounded border ${locked ? "border-terminal-down text-terminal-down" : "border-terminal-up text-terminal-up"}`}>
            Circuit: {locked ? `LOCKED → ${h?.circuit?.locked_until}` : "OK"}
          </span>
          <span className="px-2 py-1 rounded border border-terminal-border text-terminal-dim">
            Feed: {a?.data_source || "…"}
          </span>
        </div>
      </div>

      {health.error && <div className="card text-terminal-down font-mono text-sm">Backend unreachable: {health.error} — is the API running on :8000?</div>}

      <div className="grid md:grid-cols-4 gap-4">
        <StatCard label="Strategies" value={String(rows.length)} sub={rows.map((r: any) => r.status.split(" ")[0]).join(" · ") || "—"} />
        <StatCard label="Consecutive losses" value={String(h?.circuit?.consecutive_losses ?? "—")} sub={`lock after ${h?.circuit?.max_consecutive_losses ?? 2} → ${h?.circuit?.lock_hours ?? 24}h`} tone={locked ? "down" : "dim"} />
        <StatCard label="EURUSD M5 bias" value={a?.smc?.bias || "—"} sub={a?.smc?.bias_source || ""} tone={a?.smc?.bias === "bullish" ? "up" : a?.smc?.bias === "bearish" ? "down" : "dim"} />
        <StatCard label="Signal" value={a?.signal?.action === "enter" ? `${a.signal.side}` : "skip"} sub={a?.signal?.reason || a?.signal?.price || ""} tone={a?.signal?.action === "enter" ? "warn" : "dim"} />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card space-y-3">
          <div className="flex justify-between items-center">
            <h2 className="font-bold">Strategies & validation status</h2>
            <Link href="/strategies" className="text-xs text-terminal-info">manage →</Link>
          </div>
          {rows.map((s: any) => (
            <div key={s.name} className="flex items-center justify-between py-2 border-b border-terminal-border/50 last:border-0">
              <div>
                <div className="font-mono text-sm">{s.name}</div>
                <div className="text-xs text-terminal-dim font-mono">{s.symbol} {s.timeframe} · mode: {s.mode}</div>
              </div>
              <StatusBadge status={s.status} />
            </div>
          ))}
          {rows.length === 0 && <p className="text-terminal-dim text-sm">No strategies yet.</p>}
        </div>

        <div className="card space-y-3">
          <div className="flex justify-between items-center">
            <h2 className="font-bold">Latest structure — EURUSD M5</h2>
            <Link href="/live" className="text-xs text-terminal-info">open terminal →</Link>
          </div>
          {a ? (
            <div className="grid grid-cols-2 gap-4">
              <Checklist items={a.smc?.checklist} compact />
              <div>
                <ConfidenceBar value={a.confluence?.score} />
                <p className="text-xs font-mono text-terminal-dim mt-2">
                  Valuation: {a.smc?.valuation?.zone || "—"} · FVGs: {(a.smc?.active_fvgs || []).length}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-terminal-dim text-sm">{analysis.error || "loading…"}</p>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="font-bold mb-2">Validation pipeline</h2>
        <p className="text-sm text-terminal-dim font-mono">
          Unvalidated → <Link href="/backtest" className="text-terminal-info">Backtest (≥30 trades, expectancy&gt;0)</Link> → Paper trade (≥30 trades) → Live Auto unlocks.
          No strategy skips the gate. No performance numbers are shown without real data behind them.
        </p>
      </div>
    </div>
  );
}
