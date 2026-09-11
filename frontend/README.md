# Project Zero — Web Terminal (Next.js)

Real-time SMC/ICT dashboard. Talks to the FastAPI backend **only through
same-origin `/api/*` rewrites** (see `next.config.js`) — browser code never
calls localhost directly, so iframe previews and Vercel deployments work.

## Dev

```bash
npm install
npm run dev   # http://localhost:3000 (backend expected on :8000)
```

Set `NEXT_PUBLIC_API_BASE` to point rewrites at a remote backend (e.g. the
Windows VPS in production).
