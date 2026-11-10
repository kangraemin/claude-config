// GA 리포트 웹(ga-report.remin1994.workers.dev). 정적 페이지 + 갱신 요청 한 칸(KV).
// 갱신 버튼 → POST /api/refresh 가 요청 시각을 적는다. 맥의 ga_web/sync.sh(launchd 1분)가 읽고
// 오늘 0시~지금 리포트를 다시 뽑아 배포한다. 페이지는 /api/state 와 /live.json 을 보고 끝나면 새로 읽는다.
export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    const j = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
    if (u.pathname === '/api/state') return j({ req: Number(await env.ga_report.get('req') || 0) });
    if (u.pathname === '/api/refresh' && req.method === 'POST') {
      const now = Date.now(), last = Number(await env.ga_report.get('req') || 0);
      if (now - last < 120000) return j({ req: last, dup: true });  // 2분 안에 또 누르면 같은 요청으로 본다
      await env.ga_report.put('req', String(now));
      return j({ req: now });
    }
    return env.ASSETS.fetch(req);
  },
};
