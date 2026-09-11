"use client";
import { Analysis } from "@/lib/types";
import Checklist from "./Checklist";
import ConfidenceBar from "./ConfidenceBar";

export default function SignalPanel({ analysis }: { analysis: Analysis }) {
  const sig = analysis.signal;
  const isEnter = sig.action === "enter";
  const long = sig.side === "buy";
  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-bold">Signal — {analysis.symbol} {analysis.timeframe}</h3>
        <span
          className={`text-xs font-mono px-2 py-1 rounded border ${
            isEnter
              ? long
                ? "bg-terminal-up/20 text-terminal-up border-terminal-up"
                : "bg-terminal-down/20 text-terminal-down border-terminal-down"
              : "bg-gray-600/20 text-gray-300 border-gray-500"
          }`}
        >
          {isEnter ? (long ? "▲ LONG" : "▼ SHORT") : `SKIP — ${sig.reason || "no setup"}`}
        </span>
      </div>

      {isEnter && (
        <div className="grid grid-cols-3 gap-2 font-mono text-sm">
          <div><div className="text-terminal-dim text-xs">Entry</div>{sig.price?.toFixed(5)}</div>
          <div><div className="text-terminal-dim text-xs">SL</div><span className="text-terminal-down">{sig.sl?.toFixed(5)}</span></div>
          <div><div className="text-terminal-dim text-xs">TP</div><span className="text-terminal-up">{sig.tp?.toFixed(5)}</span></div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs uppercase text-terminal-dim mb-2">Rule checklist</h4>
          <Checklist items={analysis.smc.checklist} />
          {analysis.explanation && (
            <p className="text-xs text-terminal-dim mt-2 font-mono">
              Bias: {analysis.smc.bias} ({analysis.smc.bias_source || "—"}) · Valuation:{" "}
              {analysis.smc.valuation?.zone || "—"} ({analysis.smc.valuation?.position_pct?.toFixed(0) || "?"}%)
            </p>
          )}
        </div>
        <div>
          <h4 className="text-xs uppercase text-terminal-dim mb-2">Confluence</h4>
          <ConfidenceBar value={analysis.confluence?.score} />
          {analysis.confluence && (
            <ul className="mt-2 space-y-1 text-xs font-mono text-terminal-dim">
              {Object.entries(analysis.confluence.votes).map(([k, v]) => (
                <li key={k} className="flex justify-between">
                  <span>{k}</span>
                  <span>{(v as number).toFixed(2)} × w{analysis.confluence!.weights[k]}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {analysis.ai_review && (
        <div className="border-t border-terminal-border pt-3">
          <h4 className="text-xs uppercase text-terminal-dim mb-2">
            AI review — {analysis.ai_review.provider} (advisory only)
          </h4>
          <p className="text-sm">
            <span className={`font-mono font-bold ${analysis.ai_review.verdict === "enter" ? "text-terminal-up" : "text-terminal-down"}`}>
              {analysis.ai_review.verdict.toUpperCase()}
            </span>{" "}
            <span className="font-mono text-terminal-dim">conf {analysis.ai_review.confidence}%</span>
          </p>
          <p className="text-sm text-terminal-text mt-1">{analysis.ai_review.reasoning}</p>
          {analysis.ai_review.referenced_sources.length > 0 && (
            <p className="text-xs text-terminal-dim mt-1 font-mono">
              sources: {analysis.ai_review.referenced_sources.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
