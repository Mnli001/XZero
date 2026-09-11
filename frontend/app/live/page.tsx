"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";
import SignalPanel from "@/components/SignalPanel";

const CandleChart = dynamic(() => import("@/components/CandleChart"), { ssr: false });

const SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"];
const TFS = ["M1", "M5", "M15", "H1"];

export default function Live() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [tf, setTf] = useState("M5");
  const [withAI, setWithAI] = useState(false);
  const [execResult, setExecResult] = useState<any>(null);
  const [execBusy, setExecBusy] = useState(false);
  const [balance, setBalance] = useState("10000");

  const { data: a, error, refresh } = usePoll(() => api.analysis(symbol, tf, withAI), 8000, [symbol, tf, withAI]);
  const paper = usePoll(() => api.paper(), 8000);

  async function onExecute() {
    setExecBusy(true);
    setExecResult(null);
    try {
      const r = await api.execute({ symbol, timeframe: tf, balance: parseFloat(balance) || 10000, use_ai: withAI });
      setExecResult({ ok: true, r });
    } catch (e: any) {
      setExecResult({ ok: false, error: e.message });
    } finally {
      setExecBusy(false);
      refresh();
    }
  }

  const sig = a?.signal;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold">Live Terminal</h1>
        <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="!w-auto">
          {SYMBOLS.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select value={tf} onChange={(e) => setTf(e.target.value)} className="!w-auto">
          {TFS.map((t) => <option key={t}>{t}</option>)}
        </select>
        <label className="text-sm font-mono flex items-center gap-2 text-terminal-dim">
          <input type="checkbox" checked={withAI} onChange={(e) => setWithAI(e.target.checked)} className="!w-auto" />
          AI review (advisory)
        </label>
        <span className="text-xs font-mono text-terminal-dim ml-auto">
          {a ? `${a.time} · ${a.data_source} feed · mode: ${a.strategy?.mode}` : error || "connecting…"}
        </span>
      </div>

      {error && !a && <div className="card text-terminal-down font-mono text-sm">Backend unreachable: {error}</div>}

      {a && (
        <>
          <CandleChart
            candles={a.candles}
            fvgs={a.smc?.active_fvgs}
            sweepLevel={a.smc?.sweep?.level ?? null}
            equilibrium={a.smc?.valuation?.equilibrium ?? null}
            sl={sig?.action === "enter" ? sig.sl : null}
            tp={sig?.action === "enter" ? sig.tp : null}
          />
          <div className="grid lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2"><SignalPanel analysis={a} /></div>
            <div className="card space-y-3 h-fit">
              <h3 className="font-bold">Execute pipeline</h3>
              <p className="text-xs text-terminal-dim font-mono">
                Fresh analysis → AI advisory → server-side risk → mode routing. Every step is journaled.
              </p>
              <label className="text-xs font-mono text-terminal-dim">Account balance
                <input value={balance} onChange={(e) => setBalance(e.target.value)} className="mt-1" />
              </label>
              <button className="btn-primary w-full" disabled={execBusy || sig?.action !== "enter"} onClick={onExecute}>
                {execBusy ? "Routing…" : sig?.action === "enter" ? `Send ${sig.side?.toUpperCase()} via pipeline` : "No entry — pipeline idle"}
              </button>
              {!sig || sig.action !== "enter" ? (
                <p className="text-xs font-mono text-terminal-dim">Why no trade: {sig?.reason || "…"}</p>
              ) : null}
              {execResult && (
                <pre className={`text-xs font-mono p-2 rounded overflow-auto max-h-48 ${execResult.ok ? "bg-terminal-bg" : "bg-terminal-down/10 text-terminal-down"}`}>
                  {JSON.stringify(execResult.ok ? execResult.r : execResult.error, null, 2)}
                </pre>
              )}
            </div>
          </div>
          <div className="card">
            <h3 className="font-bold mb-2">Paper account <span className="font-mono text-sm text-terminal-dim">balance {paper.data?.balance}</span></h3>
            {paper.data?.positions?.length ? (
              <table className="term">
                <thead><tr><th>ID</th><th>Symbol</th><th>Side</th><th>Lots</th><th>Entry</th><th>SL</th><th>TP</th><th>Conf</th></tr></thead>
                <tbody>
                  {paper.data.positions.map((p: any) => (
                    <tr key={p.id}><td>{p.id}</td><td>{p.symbol}</td><td>{p.side}</td><td>{p.lots}</td><td>{p.entry}</td><td>{p.sl}</td><td>{p.tp}</td><td>{p.confidence}</td></tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-sm text-terminal-dim font-mono">No open paper positions. Paper metrics: {paper.data?.metrics ? `${paper.data.metrics.trade_count} trades · expectancy R ${paper.data.metrics.expectancy_r}` : "—"}</p>}
          </div>
        </>
      )}
    </div>
  );
}
