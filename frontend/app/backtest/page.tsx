"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import StatCard from "@/components/StatCard";

const EquityChart = dynamic(() => import("@/components/EquityChart"), { ssr: false });

function fmt(v: any, digits = 2) {
  if (v === null || v === undefined) return "—";
  return typeof v === "number" ? v.toFixed(digits) : String(v);
}

export default function Backtest() {
  const [csv, setCsv] = useState("/tmp/EURUSD_M5_SYNTHETIC.csv");
  const [symbol, setSymbol] = useState("EURUSD");
  const [tf, setTf] = useState("M5");
  const [minConf, setMinConf] = useState("55");
  const [rr, setRr] = useState("2.0");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [reports, setReports] = useState<any[]>([]);
  const [detail, setDetail] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadReports() {
    try { setReports((await api.backtestReports()).reports || []); } catch {}
  }
  useEffect(() => { loadReports(); }, []);

  async function run() {
    setRunning(true); setError(null); setResult(null);
    try {
      const r = await api.backtestRun({
        csv_path: csv, symbol, timeframe: tf,
        strategy_params: { min_confluence: parseFloat(minConf) || 55, risk_reward: parseFloat(rr) || 2.0 },
        risk_pct: 1.0, n_splits: 3,
      });
      setResult(r);
      loadReports();
    } catch (e: any) { setError(e.message); }
    finally { setRunning(false); }
  }

  async function openReport(id: string) {
    try { setDetail(await api.backtestReport(id)); } catch (e: any) { setError(e.message); }
  }

  const shown = result || detail;
  const oos = shown?.oos_overall;
  const equity = shown?.folds?.flatMap((f: any) => f.equity || []) || [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Backtest Engine</h1>
      <p className="text-sm text-terminal-dim font-mono">
        Walk-forward out-of-sample evaluation with spread + slippage costs. Only passing reports move a strategy to Backtested.
        CSV path is on the <b>backend server</b> (columns: time,open,high,low,close[,spread]).
      </p>

      <div className="card grid md:grid-cols-6 gap-3 items-end">
        <label className="md:col-span-2 text-xs font-mono text-terminal-dim">CSV path<input value={csv} onChange={(e) => setCsv(e.target.value)} className="mt-1" /></label>
        <label className="text-xs font-mono text-terminal-dim">Symbol<input value={symbol} onChange={(e) => setSymbol(e.target.value)} className="mt-1" /></label>
        <label className="text-xs font-mono text-terminal-dim">TF<input value={tf} onChange={(e) => setTf(e.target.value)} className="mt-1" /></label>
        <label className="text-xs font-mono text-terminal-dim">Min confluence<input value={minConf} onChange={(e) => setMinConf(e.target.value)} className="mt-1" /></label>
        <label className="text-xs font-mono text-terminal-dim">Risk:reward<input value={rr} onChange={(e) => setRr(e.target.value)} className="mt-1" /></label>
        <button className="btn-primary md:col-span-6" disabled={running} onClick={run}>{running ? "Running walk-forward…" : "Run backtest"}</button>
      </div>
      {error && <div className="card text-terminal-down font-mono text-sm">{error}</div>}

      {shown && (
        <>
          <div className={`card border-l-4 ${shown.gate?.passed ? "border-l-terminal-up" : "border-l-terminal-down"}`}>
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="font-bold">Gate verdict: {shown.gate?.passed ? "PASSED → Backtested" : "FAILED → stays Unvalidated"}</h2>
              <span className="font-mono text-xs text-terminal-dim">{shown.report_id} · {shown.bars} bars · {shown.range?.[0]} → {shown.range?.[1]}</span>
              <span className={`font-mono text-xs px-2 py-1 rounded border ${shown.data_quality?.status === "ok" ? "border-terminal-up text-terminal-up" : "border-terminal-accent text-terminal-accent"}`}>
                data: {shown.data_quality?.status} ({shown.data_quality?.gap_count} gaps)
              </span>
            </div>
            {shown.gate?.checks && (
              <div className="flex gap-3 mt-2 font-mono text-xs flex-wrap">
                {Object.entries(shown.gate.checks).map(([k, v]) => (
                  <span key={k} className={v ? "text-terminal-up" : "text-terminal-down"}>{v ? "✓" : "✗"} {k}</span>
                ))}
              </div>
            )}
          </div>

          {oos && (
            <div className="grid md:grid-cols-6 gap-4">
              <StatCard label="OOS trades" value={String(oos.trade_count)} tone={oos.trade_count >= 30 ? "up" : "warn"} />
              <StatCard label="Win rate" value={oos.win_rate != null ? `${fmt(oos.win_rate, 1)}%` : "insufficient data"} />
              <StatCard label="Expectancy R" value={oos.expectancy_r != null ? fmt(oos.expectancy_r, 3) : "insufficient data"} tone={oos.expectancy_r > 0 ? "up" : "down"} />
              <StatCard label="Max DD" value={`${fmt(oos.max_drawdown_pct)}%`} tone={oos.max_drawdown_pct <= 25 ? "up" : "down"} />
              <StatCard label="Profit factor" value={fmt(oos.profit_factor)} tone={(oos.profit_factor || 0) >= 1.1 ? "up" : "down"} />
              <StatCard label="Sharpe" value={fmt(oos.sharpe)} />
            </div>
          )}
          {oos?.note && oos.note !== "ok" && <p className="font-mono text-xs text-terminal-accent">{oos.note}</p>}

          <div className="card">
            <h3 className="font-bold mb-2">Out-of-sample equity (concatenated folds)</h3>
            <EquityChart equity={equity} />
          </div>

          {shown.folds && (
            <div className="card">
              <h3 className="font-bold mb-2">Folds</h3>
              <table className="term">
                <thead><tr><th>Fold</th><th>Test bars</th><th>Trades</th><th>Win%</th><th>Exp R</th><th>MaxDD%</th><th>PF</th></tr></thead>
                <tbody>
                  {shown.folds.map((f: any) => (
                    <tr key={f.name}><td>{f.name}</td><td>{f.test_bars?.join("–")}</td><td>{f.metrics?.trade_count}</td>
                      <td>{fmt(f.metrics?.win_rate, 1)}</td><td>{fmt(f.metrics?.expectancy_r, 3)}</td>
                      <td>{fmt(f.metrics?.max_drawdown_pct)}</td><td>{fmt(f.metrics?.profit_factor)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <div className="card">
        <h3 className="font-bold mb-2">Saved reports</h3>
        {reports.length === 0 && <p className="text-sm text-terminal-dim font-mono">No reports yet — run your first backtest above.</p>}
        <table className="term">
          <thead><tr><th>ID</th><th>Created</th><th>Symbol</th><th>TF</th><th>Trades</th><th>Exp R</th><th>MaxDD%</th><th>Data</th><th></th></tr></thead>
          <tbody>
            {reports.map((r: any) => (
              <tr key={r.report_id}>
                <td>{r.report_id}</td><td>{(r.created_at || "").slice(0, 16).replace("T", " ")}</td>
                <td>{r.symbol}</td><td>{r.timeframe}</td><td>{r.oos_overall?.trade_count}</td>
                <td>{fmt(r.oos_overall?.expectancy_r, 3)}</td><td>{fmt(r.oos_overall?.max_drawdown_pct)}</td>
                <td>{r.data_quality?.status}</td>
                <td><button className="btn !py-1 !px-2" onClick={() => openReport(r.report_id)}>open</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
