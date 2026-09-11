"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/live", label: "Live Terminal" },
  { href: "/backtest", label: "Backtest" },
  { href: "/strategies", label: "Strategies" },
  { href: "/risk", label: "Risk" },
  { href: "/journal", label: "Journal" },
  { href: "/knowledge", label: "Knowledge" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <header className="border-b border-terminal-border bg-terminal-panel sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6 flex-wrap">
        <Link href="/" className="font-bold text-lg tracking-tight">
          PROJECT<span className="text-terminal-accent">ZERO</span>
          <span className="ml-2 text-xs font-mono text-terminal-dim">SMC/ICT terminal</span>
        </Link>
        <nav className="flex gap-1 flex-wrap">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`px-3 py-1.5 rounded text-sm ${
                path === l.href
                  ? "bg-terminal-border text-white"
                  : "text-terminal-dim hover:text-white hover:bg-terminal-border/50"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
