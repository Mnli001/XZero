export default function ConfidenceBar({ value }: { value?: number | null }) {
  if (value == null) return <p className="text-terminal-dim text-sm">data insufficient</p>;
  const pct = Math.max(0, Math.min(100, value));
  const color = pct >= 70 ? "bg-terminal-up" : pct >= 45 ? "bg-terminal-accent" : "bg-terminal-down";
  return (
    <div>
      <div className="flex justify-between text-xs font-mono mb-1">
        <span className="text-terminal-dim">Confluence</span>
        <span>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded bg-terminal-border overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[11px] text-terminal-dim mt-1">Relative confluence measure — NOT a win probability.</p>
    </div>
  );
}
