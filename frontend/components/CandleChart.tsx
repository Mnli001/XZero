"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType, IChartApi, ISeriesApi } from "lightweight-charts";

interface Props {
  candles: { time: string; open: number; high: number; low: number; close: number }[];
  fvgs?: { top: number; bottom: number; direction: string }[];
  sweepLevel?: number | null;
  equilibrium?: number | null;
  sl?: number | null;
  tp?: number | null;
  height?: number;
}

export default function CandleChart({ candles, fvgs, sweepLevel, equilibrium, sl, tp, height = 420 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: "#11161f" }, textColor: "#8b94a3" },
      grid: { vertLines: { color: "#1e2633" }, horzLines: { color: "#1e2633" } },
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    chartRef.current = chart;
    const series = chart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
      borderVisible: false,
    });

    const data = candles.map((c) => ({
      time: Math.floor(new Date(c.time).getTime() / 1000) as any,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    // de-dup timestamps (mock feed can repeat)
    const seen = new Set<number>();
    const clean = data.filter((d) => (seen.has(d.time) ? false : (seen.add(d.time), true)));
    series.setData(clean);

    (fvgs || []).slice(-3).forEach((z) => {
      const color = z.direction === "bullish" ? "rgba(38,166,154,0.9)" : "rgba(239,83,80,0.9)";
      series.createPriceLine({ price: z.top, color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "FVG" });
      series.createPriceLine({ price: z.bottom, color, lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "" });
    });
    if (sweepLevel) series.createPriceLine({ price: sweepLevel, color: "#f0b90b", lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: "sweep" });
    if (equilibrium) series.createPriceLine({ price: equilibrium, color: "#4da3ff", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "EQ 50%" });
    if (sl) series.createPriceLine({ price: sl, color: "#ef5350", lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: "SL" });
    if (tp) series.createPriceLine({ price: tp, color: "#26a69a", lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: "TP" });

    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current!.clientWidth }));
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [JSON.stringify(candles.slice(-5)), (fvgs || []).length, sweepLevel, equilibrium, sl, tp]);

  return <div ref={ref} className="w-full rounded overflow-hidden border border-terminal-border" />;
}
