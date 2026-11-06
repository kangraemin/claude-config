"""compare.py 결과를 사람이 읽는 보고서(Markdown)로 만든다.

usage: report.py result.json [result2.json ...] -o report.md [--ref-name iOS] [--target-name Android]
- 다른 것: 무엇이 얼마나 다른지 + 양쪽 코드 줄
- 같은 것: 왜 같은지(양쪽 코드 줄과 계산된 값) — 증명
- 판정 못 한 것: 이유(식 계산 불가, 한쪽에만 있음, 모르는 수식어)
"""
import argparse, json, os

V = {'same': '✅ 같음', 'diff': '❌ 다름', 'only_ref': '⚠️ 기준에만', 'only_target': '⚠️ 대상에만',
     'unresolved': '❓ 계산 불가', 'check': '👀 색 확인', 'count_diff': '❌ 아이 수 다름', 'info': 'ℹ️ 참고'}


def fmt(v):
    if v is None: return '—'
    if isinstance(v, float): return f'{v:.2f}'.rstrip('0').rstrip('.')
    return str(v)


def where(r, base):
    if not r: return '—'
    f = os.path.relpath(r['file'], base) if base else os.path.basename(r['file'])
    return f"`{os.path.basename(f)}:{r['line']}` `{(r.get('src') or '')[:70]}`"


def name(e):
    an = e.get('anchor')
    lab = f"{an[0]}:{an[1]}" if an else e['callee']
    return f"{e['role']} {lab} ({e['path'].split('/')[-1]})"


def dedupe(items):
    """같은 정의를 여러 번 부른 경우(행이 2개 등) 같은 줄·같은 값은 한 줄로 묶고 ×N 표시."""
    seen = {}; out = []
    for p, r in items:
        key = (r['key'], r['ref'] and (r['ref']['file'], r['ref']['line'], str(r['ref']['value'])),
               r['target'] and (r['target']['file'], r['target']['line'], str(r['target']['value'])))
        if key in seen: seen[key][2] += 1; continue
        seen[key] = [p, r, 1]; out.append(seen[key])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('results', nargs='+'); ap.add_argument('-o', required=True)
    ap.add_argument('--ref-name', default='기준'); ap.add_argument('--target-name', default='대상')
    a = ap.parse_args()
    L = [f'# 크기 요소 대조 보고서 ({a.ref_name} → {a.target_name})', '']
    L.append('- 값은 코드(iOS·Android)와 Figma 노드에서 스크립트로 뽑았다. LLM 판단 없음.')
    L.append('- 아이콘은 틀이 아니라 실제로 그려지는 그림 크기(glyph)로 비교했다.')
    L.append('- 스택 간격은 spacing + 고정 Spacer 를 합친 실제 아이 사이 간격으로 비교했다.')
    L.append('')
    summary = []
    body = []
    for rp in a.results:
        R = json.load(open(rp)); tol = R['tol']
        c = {}
        for p in R['pairs']:
            for r in p['rows']: c[r['verdict']] = c.get(r['verdict'], 0) + 1
        summary.append(f"| {R['ref']} ↔ {R['target']} | {len(R['pairs'])} | {c.get('same', 0)} | {c.get('diff', 0) + c.get('count_diff', 0)} | "
                       f"{c.get('only_ref', 0) + c.get('only_target', 0)} | {c.get('unresolved', 0) + c.get('check', 0)} | {len(R['only_ref'])} / {len(R['only_target'])} |")
        body.append(f"## {R['ref']} ↔ {R['target']}  (허용 오차 {tol}pt)")
        body.append('')
        diffs = dedupe([(p, r) for p in R['pairs'] for r in p['rows'] if r['verdict'] in ('diff', 'count_diff')])
        body.append(f'### ❌ 다른 것 {len(diffs)}개')
        body.append('')
        if diffs:
            body.append(f'| 요소 | 속성 | {a.ref_name} | {a.target_name} | 차이 | {a.ref_name} 근거 | {a.target_name} 근거 |')
            body.append('|---|---|---|---|---|---|---|')
            for p, r, n in diffs:
                body.append(f"| {name(p['ref'])}{' ×' + str(n) if n > 1 else ''} | {r['key']} | {fmt(r['ref'] and r['ref']['value'])} | {fmt(r['target'] and r['target']['value'])} | "
                            f"{fmt(r['delta']) if r['delta'] is not None else '—'} | {where(r['ref'], None)} | {where(r['target'], None)} |")
            body.append('')
        half = dedupe([(p, r) for p in R['pairs'] for r in p['rows'] if r['verdict'] in ('only_ref', 'only_target', 'unresolved', 'check')])
        body.append(f'### ⚠️ 판정 못 한 것·한쪽에만 있는 속성 {len(half)}개')
        body.append('')
        if half:
            body.append(f'| 요소 | 속성 | 판정 | {a.ref_name} | {a.target_name} | 근거 |')
            body.append('|---|---|---|---|---|---|')
            for p, r, n in half:
                body.append(f"| {name(p['ref'])}{' ×' + str(n) if n > 1 else ''} | {r['key']} | {V[r['verdict']]} | {fmt(r['ref'] and r['ref']['value'])} | {fmt(r['target'] and r['target']['value'])} | "
                            f"{where(r['ref'] or r['target'], None)} |")
            body.append('')
        um = sorted({(name(p['ref']), s, m) for p in R['pairs'] for s in ('ref', 'target') for m in p['unknown_mods'][s]})
        if um:
            body.append(f'### 🔍 스크립트가 크기를 못 읽은 수식어 {len(um)}개 (직접 확인 필요)')
            body.append('')
            for nm_, s, m in um:
                body.append(f"- {nm_} · {a.ref_name if s == 'ref' else a.target_name}: `{m}`")
            body.append('')
        same = dedupe([(p, r) for p in R['pairs'] for r in p['rows'] if r['verdict'] == 'same'])
        body.append(f'### ✅ 같은 것 {len(same)}개 — 같다는 근거')
        body.append('')
        body.append(f'| 요소 | 속성 | 값 | {a.ref_name} 근거 | {a.target_name} 근거 |')
        body.append('|---|---|---|---|---|')
        for p, r, n in same:
            v = fmt(r['ref']['value']); vb = fmt(r['target']['value'])
            body.append(f"| {name(p['ref'])}{' ×' + str(n) if n > 1 else ''} | {r['key']} | {v if v == vb else v + ' / ' + vb} | {where(r['ref'], None)} | {where(r['target'], None)} |")
        body.append('')
        if R['only_ref'] or R['only_target']:
            body.append(f"### 짝 못 찾은 요소 ({a.ref_name} {len(R['only_ref'])} / {a.target_name} {len(R['only_target'])})")
            body.append('')
            for side, lst in ((a.ref_name, R['only_ref']), (a.target_name, R['only_target'])):
                for e in lst:
                    pv = ', '.join(f"{k}={fmt(v['value'])}" for k, v in list(e['props'].items())[:6])
                    body.append(f"- {side}: {name(e)} `{os.path.basename(e['file'])}:{e['line']}` {pv}")
            body.append('')
    L.append('| 화면 | 짝 지은 요소 | ✅ 같음 | ❌ 다름 | ⚠️ 한쪽만 | ❓ 판정 못 함 | 짝 없는 요소(기준/대상) |')
    L.append('|---|---|---|---|---|---|---|')
    L += summary
    L.append('')
    L += body
    open(a.o, 'w').write('\n'.join(L))
    print(f'보고서 → {a.o}')


if __name__ == '__main__':
    main()
