// 주소만 알면 누구나 보던 걸 막는다(사용자 11/10 "저거 남이보면어캄"). ?k=키로 한 번 열면 1년 쿠키.
export function gate(req, env) {
  const u = new URL(req.url);
  const key = env.PRIVATE_KEY;
  if (!key) return new Response('설정 오류', { status: 500 });
  const k = u.searchParams.get('k');
  if (k === key) {
    u.searchParams.delete('k');
    return new Response(null, { status: 302, headers: { location: u.pathname + u.search, 'set-cookie': `pk=${key}; Max-Age=31536000; Path=/; HttpOnly; Secure; SameSite=Lax` } });
  }
  const c = (req.headers.get('cookie') || '').split(/;\s*/).find(x => x.startsWith('pk='));
  if (c && c.slice(3) === key) return null;
  return new Response('비공개 페이지예요', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8', 'x-robots-tag': 'noindex' } });
}
