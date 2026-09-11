import { Checklist as TChecklist } from "@/lib/types";

const LABELS: Record<string, string> = {
  sweep: "Liquidity sweep",
  choch: "CHoCH",
  structure_break: "Structure break (BOS/CHoCH)",
  fvg: "Active FVG",
  valuation: "Premium/Discount aligned",
  retest: "Retest / trigger",
};

export default function Checklist({ items, compact }: { items?: TChecklist | null; compact?: boolean }) {
  if (!items) return <p className="text-terminal-dim text-sm">No checklist data yet.</p>;
  return (
    <ul className={compact ? "space-y-1" : "space-y-1.5"}>
      {Object.entries(items).map(([k, v]) => (
        <li key={k} className="flex items-center gap-2 text-sm font-mono">
          <span className={v ? "text-terminal-up" : "text-terminal-down"}>{v ? "✓" : "✗"}</span>
          <span className={v ? "text-terminal-text" : "text-terminal-dim"}>
            {LABELS[k] || k}
          </span>
        </li>
      ))}
    </ul>
  );
}
