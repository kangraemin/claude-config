import { gate } from './gate.js';
export default {
  async fetch(req, env) {
    const g = gate(req, env);
    if (g) return g;
    const u = new URL(req.url);
    const j = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
    if (u.pathname === '/api/state') return j({ req: Number(await env.ga_report.get('req') || 0) });
    if (u.pathname === '/api/refresh' && req.method === 'POST') {
      const now = Date.now(), last = Number(await env.ga_report.get('req') || 0);
      if (now - last < 120000) return j({ req: last, dup: true });
      await env.ga_report.put('req', String(now));
      return j({ req: now });
    }
    return env.ASSETS.fetch(req);
  },
};
