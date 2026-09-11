"use client";
import { useCallback, useEffect, useRef, useState } from "react";

// Polling-based live data (works through the Next.js proxy in any environment,
// including iframe previews where raw WebSockets may be unavailable).
export function usePoll<T>(fn: () => Promise<T>, ms: number, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const refresh = useCallback(async () => {
    try {
      const d = await fnRef.current();
      setData(d);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, ms);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, ...deps]);

  return { data, error, loading, refresh };
}
