"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Knowledge() {
  const [sources, setSources] = useState<any[]>([]);
  const [policy, setPolicy] = useState("");
  const [form, setForm] = useState({ title: "", kind: "note", uri: "", content: "", tags: "" });
  const [q, setQ] = useState("fair value gap entry");
  const [results, setResults] = useState<any[]>([]);

  async function load() {
    try {
      const d = await api.knowledge();
      setSources(d.sources || []); setPolicy(d.policy || "");
    } catch {}
  }
  useEffect(() => { load(); }, []);

  async function add() {
    await api.addSource({ ...form, tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean) });
    setForm({ title: "", kind: "note", uri: "", content: "", tags: "" });
    load();
  }
  async function del(id: string) { await api.deleteSource(id); load(); }
  async function search() { setResults((await api.searchKb(q)).results || []); }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Knowledge Base</h1>
      <p className="text-sm text-terminal-dim font-mono">{policy}</p>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card space-y-2">
          <h2 className="font-bold">Curated sources ({sources.length})</h2>
          {sources.map((s: any) => (
            <div key={s.id} className="bg-terminal-bg rounded p-2 flex justify-between gap-2">
              <div className="text-sm">
                <div className="font-mono">[{s.id}] {s.title} <span className="text-terminal-dim">({s.kind})</span></div>
                <div className="text-xs text-terminal-dim truncate max-w-[420px]">{s.content}</div>
              </div>
              <button className="btn-danger !py-1" onClick={() => del(s.id)}>del</button>
            </div>
          ))}
          {sources.length === 0 && <p className="text-sm text-terminal-dim font-mono">Empty — add your first vetted source →</p>}
        </div>

        <div className="space-y-4">
          <div className="card space-y-2">
            <h2 className="font-bold">Add source (manual curation)</h2>
            <input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                {["note", "github", "paper", "book", "other"].map((k) => <option key={k}>{k}</option>)}
              </select>
              <input placeholder="URI (optional)" value={form.uri} onChange={(e) => setForm({ ...form, uri: e.target.value })} />
            </div>
            <textarea placeholder="Excerpt / summary (min 20 chars)" rows={4} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
            <input placeholder="tags, comma, separated" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
            <button className="btn-primary" onClick={add}>Add to knowledge base</button>
          </div>

          <div className="card space-y-2">
            <h2 className="font-bold">Retrieval test</h2>
            <div className="flex gap-2">
              <input value={q} onChange={(e) => setQ(e.target.value)} />
              <button className="btn" onClick={search}>Search</button>
            </div>
            {results.map((r: any) => (
              <div key={r.id} className="text-sm font-mono bg-terminal-bg rounded p-2">
                [{r.id}] {r.title} <span className="text-terminal-accent">score {r.score}</span>
                <div className="text-xs text-terminal-dim">{r.excerpt}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
