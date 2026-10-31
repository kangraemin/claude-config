#!/usr/bin/env python3
"""AI 티 자동 검사 — 실제 브라우저로 페이지를 열어 'AI가 만든 티' 신호를 숫자로 잰다.

사용:
  python3 ai_look_check.py <URL 또는 파일경로> [--width 390] [--height 844]
                           [--json out.json] [--shot out.png] [--wait 1500]

LLM 점수 대신 숫자로 판정한다. 기준값은 SKILL.md 체크리스트와 같다.
종료 코드: FAIL 항목이 있으면 1, 없으면 0.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# 기준값 (SKILL.md 체크리스트와 맞춘다)
LIMITS = {
    "tiny_text": 3,            # 13px 미만 글자 블록 (법적 고지 몇 개만 허용)
    "font_sizes": 6,           # 고유 font-size 개수 (taste-skill: 5가 천장, 토스 앱 화면 4~6)
    "font_weights": 3,         # 고유 font-weight 개수
    "accent_elems": 8,         # 강조색(채도 높은 색) 글자·배경 요소 수, 페이지 전체
    "accent_first_screen": 3,  # 첫 화면 안 강조색 요소 수 (토스: 한 화면 강조 하나)
    "accent_hues": 2,          # 강조 색상 계열 수 (브랜드 1 + 의미색 1)
    "mixed_blocks": 0,         # 한 문장(블록) 안 색 또는 굵기 다른 조각이 섞인 블록 수
    "overflow": 0,             # 가로로 화면 밖에 나간 요소 수
    "hidden_by_fixed": 0,      # 고정 하단바·헤더에 가려지는 요소 수
    "nested_cards": 0,         # 카드 안 카드
    "card_max_items": 6,       # 카드 하나 안 글자 조각 최대 수 (카드마다 미니 대시보드 방지)
    "card_size_variants": 3,   # 같은 목록 안 카드 크기 종류
    "gradients": 1,            # 그라디언트 배경 (사진 위 스크림 하나 정도)
    "emoji": 0,                # 이모지 아이콘
    "small_caps_labels": 2,    # 작은 대문자·자간 넓힌 라벨(eyebrow)
    "small_svgs": 4,           # 깨알 도식(작은 svg 차트·스파크라인)
    "colored_side_borders": 0, # 카드 한쪽만 두꺼운 색 테두리
}

JS = r"""
(() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const out = {};
  const vis = el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const parseRGB = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}; };
  const hsl = ({r,g,b}) => { r/=255; g/=255; b/=255; const mx=Math.max(r,g,b), mn=Math.min(r,g,b);
    let h=0,s=0; const l=(mx+mn)/2; const d=mx-mn;
    if (d) { s = l>0.5 ? d/(2-mx-mn) : d/(mx+mn);
      h = mx===r ? ((g-b)/d + (g<b?6:0)) : mx===g ? ((b-r)/d+2) : ((r-g)/d+4); h*=60; }
    return {h,s,l}; };
  const isAccent = c => { const p = parseRGB(c); if (!p || p.a < 0.5) return null;
    const x = hsl(p); return (x.s >= 0.45 && x.l >= 0.25 && x.l <= 0.75) ? Math.round(x.h/30)%12 : null; };
  const label = el => { const t = (el.innerText||'').trim().replace(/\s+/g,' ').slice(0,40);
    return `${el.tagName.toLowerCase()}${el.className && typeof el.className==='string' ? '.'+el.className.trim().split(/\s+/)[0] : ''} "${t}"`; };

  // 직접 글자를 가진 보이는 요소
  const all = [...document.body.querySelectorAll('*')].filter(el => !['SCRIPT','STYLE','NOSCRIPT','SVG','PATH'].includes(el.tagName));
  const textEls = all.filter(el => [...el.childNodes].some(n => n.nodeType===3 && n.textContent.trim().length) && vis(el));
  out.text_elems = textEls.length;

  const sizes = {}, weights = {}; const tiny = [];
  // footer(법적 고지·사업자 정보)는 글자 크기 검사에서 뺀다
  textEls.filter(el => !el.closest('footer')).forEach(el => { const s = getComputedStyle(el); const fs = Math.round(parseFloat(s.fontSize)*2)/2;
    sizes[fs] = (sizes[fs]||0)+1; weights[s.fontWeight] = (weights[s.fontWeight]||0)+1;
    if (fs < 13) tiny.push(`${fs}px ${label(el)}`); });
  out.font_sizes = Object.keys(sizes).length; out.font_size_hist = sizes;
  out.font_weights = Object.keys(weights).length; out.font_weight_hist = weights;
  out.tiny_text = tiny.length; out.tiny_examples = tiny.slice(0,8);

  // 강조색
  const accent = []; const hues = {}; let firstScreen = 0;
  all.filter(vis).forEach(el => { const s = getComputedStyle(el);
    const hasText = textEls.includes(el);
    const hc = hasText ? isAccent(s.color) : null;
    const hb = isAccent(s.backgroundColor);
    const h = hc !== null ? hc : hb;
    if (h !== null) { accent.push(`${hc!==null?'글자':'배경'} ${s[hc!==null?'color':'backgroundColor']} ${label(el)}`);
      hues[h] = (hues[h]||0)+1;
      const r = el.getBoundingClientRect(); if (r.top + window.scrollY < vh) firstScreen++; } });
  out.accent_elems = accent.length; out.accent_examples = accent.slice(0,10);
  out.accent_first_screen = firstScreen;
  out.accent_hues = Object.keys(hues).length; out.accent_hue_hist = hues;

  // 한 블록 안 색/굵기 섞기
  const blockTags = new Set(['P','H1','H2','H3','H4','H5','H6','LI','DD','DT','BLOCKQUOTE','FIGCAPTION','LABEL','TD','TH']);
  const mixed = [];
  textEls.forEach(el => { const s = getComputedStyle(el);
    if (!(blockTags.has(el.tagName) || s.display==='block' || s.display==='flex')) return;
    if (el.tagName==='NAV' || el.closest('nav,footer')) return;  // 링크 나열은 제외
    const kids = [...el.querySelectorAll('span,b,strong,em,i,mark,a,small')].filter(k => vis(k) && (k.innerText||'').trim());
    const odd = kids.filter(k => { const ks = getComputedStyle(k); return ks.color !== s.color || Math.abs(+ks.fontWeight - +s.fontWeight) >= 200; });
    if (odd.length) mixed.push(`${label(el)} ← ${odd.length}조각(${odd.slice(0,2).map(k=>'"'+k.innerText.trim().slice(0,12)+'"').join(',')})`); });
  out.mixed_blocks = mixed.length; out.mixed_examples = mixed.slice(0,10);

  // 가로 넘침
  const over = all.filter(vis).filter(el => { const r = el.getBoundingClientRect(); return r.right > vw + 1 || r.left < -1; })
    .filter(el => { let p = el.parentElement; while (p) { const s=getComputedStyle(p); if (/(auto|scroll|hidden)/.test(s.overflowX)) return false; p = p.parentElement; } return true; });
  out.page_scroll_width = document.documentElement.scrollWidth; out.viewport = [vw, vh];
  out.overflow = over.length + (document.documentElement.scrollWidth > vw + 1 ? 1 : 0);
  out.overflow_examples = over.slice(0,6).map(label);

  // 카드
  const isCard = el => { const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    if (r.width < 80 || r.height < 40) return false;
    const rad = parseFloat(s.borderTopLeftRadius)||0;
    const border = (parseFloat(s.borderTopWidth)||0) > 0 && s.borderTopStyle !== 'none';
    const shadow = s.boxShadow && s.boxShadow !== 'none';
    const bg = parseRGB(s.backgroundColor); const pbg = el.parentElement ? parseRGB(getComputedStyle(el.parentElement).backgroundColor) : null;
    const bgStep = bg && bg.a > 0.3 && (!pbg || Math.abs(bg.r-pbg.r)+Math.abs(bg.g-pbg.g)+Math.abs(bg.b-pbg.b) > 6);
    return rad > 4 && (border || shadow || bgStep) && (el.innerText||'').trim().length > 0; };
  const cards = all.filter(vis).filter(isCard);
  const nested = cards.filter(c => cards.some(o => o !== c && o.contains(c)));
  out.cards = cards.length; out.nested_cards = nested.length; out.nested_examples = nested.slice(0,5).map(label);
  const items = cards.filter(c => !nested.includes(c)).map(c => ({c, n: textEls.filter(t => c.contains(t)).length}));
  items.sort((a,b)=>b.n-a.n);
  out.card_max_items = items.length ? items[0].n : 0;
  out.busy_cards = items.filter(x => x.n > 6).slice(0,6).map(x => `${x.n}조각 ${label(x.c)}`);
  // 같은 부모 아래 카드 크기 종류
  const groups = new Map(); cards.filter(c => !nested.includes(c)).forEach(c => { const p = c.parentElement; if (!groups.has(p)) groups.set(p, []); groups.get(p).push(c); });
  let worst = 0, worstEx = '';
  groups.forEach((cs, p) => { if (cs.length < 3) return; const k = new Set(cs.map(c => { const r=c.getBoundingClientRect(); return Math.round(r.width/20)+'x'+Math.round(r.height/20); }));
    if (k.size > worst) { worst = k.size; worstEx = `${cs.length}개 카드 ${k.size}가지 크기 in ${label(p)}`; } });
  out.card_size_variants = worst; out.card_size_example = worstEx;

  // 기타 신호
  out.gradients = all.filter(vis).filter(el => /gradient/.test(getComputedStyle(el).backgroundImage)).length;
  const emojiRe = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F000}-\u{1F2FF}]/u;
  const emo = textEls.filter(el => emojiRe.test([...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('')));
  out.emoji = emo.length; out.emoji_examples = emo.slice(0,5).map(label);
  out.small_caps_labels = textEls.filter(el => { const s = getComputedStyle(el);
    return parseFloat(s.fontSize) <= 14 && (s.textTransform === 'uppercase' || parseFloat(s.letterSpacing) >= 1); }).length;
  out.small_svgs = [...document.querySelectorAll('svg')].filter(vis).filter(s => { const r = s.getBoundingClientRect();
    return r.width >= 20 && r.width <= 160 && r.height <= 70 && s.querySelectorAll('path,line,polyline,rect,circle').length >= 2; }).length;
  out.colored_side_borders = all.filter(vis).filter(el => { const s = getComputedStyle(el);
    const L = parseFloat(s.borderLeftWidth)||0, T = parseFloat(s.borderTopWidth)||0;
    return L >= 3 && T < 2 && isAccent(s.borderLeftColor) !== null; }).length;

  // 고정 바
  const fixed = all.filter(vis).filter(el => { const p = getComputedStyle(el).position; return p === 'fixed' || p === 'sticky'; })
    .filter(el => !all.some(o => o !== el && o.contains(el) && ['fixed','sticky'].includes(getComputedStyle(o).position)));
  out.fixed_bars = fixed.map(el => { const r = el.getBoundingClientRect(); return `${label(el)} top=${Math.round(r.top)} h=${Math.round(r.height)}`; });
  return out;
})()
"""

# 페이지 끝까지 내리며 고정 바에 가려지는 요소 찾기
JS_HIDDEN = r"""
(() => {
  const vh = window.innerHeight;
  const bars = [...document.body.querySelectorAll('*')].filter(el => { const s = getComputedStyle(el);
    return (s.position === 'fixed' || s.position === 'sticky') && s.display !== 'none' && el.getBoundingClientRect().height > 0; });
  const inBar = el => bars.some(b => b.contains(el));
  const targets = [...document.body.querySelectorAll('a,button,input,select,textarea,p,h1,h2,h3,li,label,img')]
    .filter(el => !inBar(el)).filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  const hits = [];
  // 페이지 맨 끝 상태에서, 화면 안에 있어야 할 마지막 요소들이 바에 덮였는지
  targets.forEach(el => { const r = el.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= vh) return;
    const x = Math.min(Math.max(r.left + r.width/2, 1), window.innerWidth-1);
    const y = Math.min(Math.max(r.top + r.height/2, 1), vh-1);
    const top = document.elementFromPoint(x, y);
    if (top && top !== el && !el.contains(top) && inBar(top)) hits.push(`${el.tagName.toLowerCase()} "${(el.innerText||el.alt||'').trim().slice(0,30)}"`); });
  return hits;
})()
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--width", type=int, default=390)
    ap.add_argument("--height", type=int, default=844)
    ap.add_argument("--json")
    ap.add_argument("--shot")
    ap.add_argument("--wait", type=int, default=1500)
    a = ap.parse_args()
    url = a.url
    if not url.startswith(("http://", "https://", "file://")):
        url = Path(url).resolve().as_uri()

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": a.width, "height": a.height}, device_scale_factor=2,
                        is_mobile=a.width < 600, has_touch=a.width < 600)
        pg.goto(url, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(a.wait)
        # 지연 로딩 요소를 깨우려고 끝까지 한 번 내렸다 올림
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(600)
        pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(400)
        r = pg.evaluate(JS)
        hidden = set()
        total = pg.evaluate("document.documentElement.scrollHeight")
        y = 0
        while y < total:
            pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(120)
            hidden.update(pg.evaluate(JS_HIDDEN))
            y += int(a.height * 0.6)
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(200)
        end_hidden = pg.evaluate(JS_HIDDEN)
        hidden.update(end_hidden)
        # 중간 스크롤에선 잠깐 덮이는 게 정상이므로, 판정은 '맨 끝에서도 덮인 것'만
        r["hidden_by_fixed"] = len(end_hidden)
        r["hidden_examples"] = end_hidden[:8]
        r["covered_while_scrolling"] = len(hidden)
        if a.shot:
            pg.evaluate("window.scrollTo(0,0)"); pg.screenshot(path=a.shot, full_page=False)
        b.close()

    fails = []
    print(f"AI 티 검사  {a.url}  @ {a.width}x{a.height}")
    print("-" * 64)
    for k, lim in LIMITS.items():
        v = r.get(k, 0)
        ok = v <= lim
        if not ok:
            fails.append(k)
        print(f"{'PASS' if ok else 'FAIL'}  {k:<22} {v:>5}  (기준 ≤{lim})")
    print("-" * 64)
    print(f"글자 블록 {r['text_elems']}개 · 카드 {r['cards']}개 · 글자 크기 분포 {r['font_size_hist']}")
    print(f"굵기 분포 {r['font_weight_hist']} · 강조 색상 계열 {r['accent_hue_hist']}")
    print(f"고정 바: {r['fixed_bars'] or '없음'}")
    for key in ["tiny_examples", "accent_examples", "mixed_examples", "overflow_examples", "hidden_examples",
                "nested_examples", "busy_cards", "card_size_example", "emoji_examples"]:
        v = r.get(key)
        if v:
            print(f"\n[{key}]")
            for line in (v if isinstance(v, list) else [v])[:8]:
                print("  -", line)
    print(f"\n결과: {'FAIL ' + str(len(fails)) + '개: ' + ', '.join(fails) if fails else 'PASS'}")
    print("주의: 숫자 PASS는 '나쁜 신호 없음'일 뿐 '좋은 디자인'이 아니다. 사용자 캡처와 전후 비교를 따로 한다.")
    if a.json:
        r["fails"] = fails
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
