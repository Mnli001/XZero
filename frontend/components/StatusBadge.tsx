const COLORS: Record<string, string> = {
  Unvalidated: "bg-gray-600/30 text-gray-300 border-gray-500",
  Backtested: "bg-blue-600/20 text-blue-300 border-blue-500",
  "Paper-Tested": "bg-yellow-600/20 text-yellow-300 border-yellow-500",
  "Live-Verified": "bg-green-600/20 text-green-300 border-green-500",
};

export default function StatusBadge({ status }: { status: string }) {
  const key = Object.keys(COLORS).find((k) => status.startsWith(k)) || "Unvalidated";
  return (
    <span className={`text-xs font-mono px-2 py-1 rounded border ${COLORS[key]}`}>
      {status}
    </span>
  );
}
