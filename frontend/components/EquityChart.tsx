"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType } from "lightweight-charts";

export default function EquityChart({ equity, height = 260 }: { equity: number[]; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || equity.length < 2) return;
    const chart = createChart(ref.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: "#11161f" }, textColor: "#8b94a3" },
      grid: { vertLines: { color: "#1e2633" }, horzLines: { color: "#1e2633" } },
    });
    const series = chart.addAreaSeries({
      topColor: "rgba(38,166,154,0.6)",
      bottomColor: "rgba(38,166,154,0.05)",
      lineColor: "#26a69a",
      lineWidth: 2,
    });
    series.setData(equity.map((v, i) => ({ time: (i + 1) as any, value: v })));
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current!.clientWidth }));
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [equity.length]);
  if (equity.length < 2) return <p className="text-terminal-dim text-sm">Not enough equity points.</p>;
  return <div ref={ref} className="w-full rounded overflow-hidden border border-terminal-border" />;
}
