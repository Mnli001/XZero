"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

const KINDS = ["", "SIGNAL", "SKIP", "FILL", "CLOSE", "RISK_BLOCK", "SYSTEM_ERROR"];

export default function Journal() {
  const [kind, setKind] = useState("");
  const { data } = usePoll(() => api.journal(kind || undefined), 10000, [kind]);
  const rows = data?.rows || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold">Journal</h1>
        <select value={kind} onChange={(e) => setKind(e.target.value)} className="!w-auto">
          {KINDS.map((k) => <option key={k} value={k}>{k || "all kinds"}</option>)}
        </select>
        <span className="text-xs font-mono text-terminal-dim">{data?.count || 0} records</span>
        <div className="ml-auto flex gap-2">
          <a className="btn" href="/api/journal/export.csv">Export CSV</a>
          <a className="btn" href="/api/journal/export.xlsx">Export Excel</a>
        </div>
      </div>
      <div className="card overflow-x-auto">
        <table className="term min-w-[900px]">
          <thead><tr><th>Time</th><th>Kind</th><th>Symbol</th><th>Side</th><th>Lots</th><th>Entry</th><th>Exit</th><th>P&L</th><th>R</th><th>Conf</th><th>Reason</th></tr></thead>
          <tbody>
            {rows.map((r: any, i: number) => (
              <tr key={i} className={r.kind === "SYSTEM_ERROR" ? "text-terminal-down" : r.kind === "RISK_BLOCK" ? "text-terminal-accent" : ""}>
                <td>{(r.journaled_at || "").slice(5, 19).replace("T", " ")}</td>
                <td>{r.kind}</td>
                <td>{r.symbol || "—"}</td>
                <td>{r.side || "—"}</td>
                <td>{r.lots ?? "—"}</td>
                <td>{r.entry ?? "—"}</td>
                <td>{r.exit_price ?? "—"}</td>
                <td className={r.pnl > 0 ? "text-terminal-up" : r.pnl < 0 ? "text-terminal-down" : ""}>{r.pnl ?? "—"}</td>
                <td>{r.r_multiple ?? "—"}</td>
                <td>{r.confidence ?? "—"}</td>
                <td className="max-w-[260px] truncate" title={r.reason || r.reasoning || r.error || ""}>{r.reason || r.reasoning || r.error || r.exit_reason || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="text-sm text-terminal-dim font-mono py-4">Journal is empty — signals, skips, fills and blocks will appear here.</p>}
      </div>
    </div>
  );
}
