export default function StatCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "up" | "down" | "warn" | "dim";
}) {
  const color =
    tone === "up" ? "text-terminal-up" : tone === "down" ? "text-terminal-down" : tone === "warn" ? "text-terminal-accent" : "text-terminal-text";
  return (
    <div className="bg-terminal-panel border border-terminal-border rounded p-4">
      <div className="text-xs text-terminal-dim uppercase tracking-wide">{label}</div>
      <div className={`text-xl font-mono font-bold mt-1 ${color}`}>{value}</div>
      {sub && <div className="text-xs text-terminal-dim mt-1 font-mono">{sub}</div>}
    </div>
  );
}
