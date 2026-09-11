import type { Metadata } from "next";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Project Zero — SMC/ICT Terminal",
  description: "AI-powered SMC/ICT order-flow trading terminal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
        <footer className="max-w-7xl mx-auto px-4 pb-8 text-xs text-terminal-dim font-mono">
          Project Zero · stats shown only from real backtest/paper/live data — never demo numbers · trading involves risk
        </footer>
      </body>
    </html>
  );
}
