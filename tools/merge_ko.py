# -*- coding: utf-8 -*-
r"""하스피 번역 병합(2026-10-31) — my files/실크외전번역/*.tsv → work/text/ko_script.tsv(JP·KO) · ko_sys.tsv(위치·JP·KO) · 비교 my files/실크외전번역/병합_비교.txt
  맞추기: 번역 파일 중 옛 판(sg_001~024, 추출 고치기 전 번호)은 «원문 그대로» → 안 맞으면 «위치(파일:기록)» · sg_miss·sg_sys 는 번호(새 판) + 원문 검산
  통일: 시로후지 → 시라후지 · 「@P님」「@P씨」 → 「@P 님」「@P 씨」(받은 번역 다수 쪽)
  토큰: ／ 뺀 토큰(@코드·{n}·%s) 차례가 원문과 다르면 목록(빌드 막힘) · ／(줄바꿈) 개수는 달라도 됨(창 안이면)
  줄 폭: 반각 36(전각 18 · 한글 1자 = 2 · @P = 8) — 넘으면 그 쪽(@K·@pW·{n} 사이) 안에서 낱말 단위로 다시 나눔, 쪽당 줄 수는 max(원문, 4) 까지 → 그래도 넘치면 overflow 목록
  C:/claude/utils/kiwi-venv/Scripts/python tools/merge_ko.py   (★Kiwi 필요 — 다시 나눌 때 번역자가 낱말 중간에서 끊은 줄을 붙일지 판정)"""
import csv, glob, os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'my files', '실크외전번역')
W = 36
PAGE = re.compile(r'(@K|@pW|\{\d+\})')
STRIP = re.compile(r'\{\d+\}|@pW|@F\d?|@Q\d|@[A-Za-z]|@[.}=<>/(+]')
TOK = re.compile(r'@\.|@K|@P|@B|@C|@Q\d|@\}|@=|@<|@/|@pW|@F\d?|@\(|@\+|%[-0-9]*[dsx]|\{\d+\}')
PUNCT = ',.!?~:;…、。，．！？：；～'


def width(s):
    s = s.replace('@P', 'ＰＰＰＰ').replace('@C', 'ＣＣＣＣ'); s = STRIP.sub('', s)   # @C = 인물 이름, 가장 긴 «시라후지» 8칸(2026-11-01 «컴퓨터에／／맡겨요» 빈 줄)
    s = re.sub('([%s]) +' % re.escape(PUNCT), r'\1', s)
    return sum(1 if 0xFF61 <= ord(c) <= 0xFF9F else 2 for c in s)   # ★공백·영숫자도 게임에서 전각 폭(2026-10-31 실기: 36칸 줄 뒤 빈 줄) — 반각 가나만 1


def unify(s, script=True):
    s = s.replace('시로후지', '시라후지')
    s = re.sub(r'어디(서나|서든|에서나|든지) 거울', '어디로든 거울', s)        # どこでもミラー = 그림(I-04)과 같은 «어디로든 거울»(하스피)
    s = s.replace('ㅡ', 'ー').replace('·', '・')
    if not script: return s                                              # 시스템 문자열은 반각 괄호 그대로(바이트 예산·원문도 반각)
    s = s.replace('(', '（').replace(')', '）')
    if s.count("'") % 2 == 0:                                            # 반각 ' 는 글꼴에 없음(실기 깨짐) → 원문처럼 『』(차례대로 여닫음, 줄바꿈 넘어도)
        n = [0]
        def q(m):
            n[0] += 1; return '『' if n[0] % 2 else '』'
        s = re.sub("'", q, s)                            # 글꼴에 없는 글자 → 같은 모양 전각(장음·가운뎃점)
    s = re.sub(r'@P(님|씨)', r'@P \1', s)
    return s


_KIWI = None
JOSA = {'만', '에', '에서', '을', '를', '은', '는', '도', '로', '으로', '와', '과', '고', '다고', '라고', '의', '께', '한테', '처럼', '까지', '부터', '보다', '조차', '마저', '이나'}
STANDALONE = {'나', '너', '저', '제', '내', '네', '이건', '이거', '그건', '그거', '이', '그', '저건', '저거'}


def glue(a, b):
    """번역자 줄 끝 a / 다음 줄 b 를 이을 때 공백 없이 붙일지(낱말 중간 끊김: «리듬체조／만»·«생각／하셨군요»·«카드／였죠»)
    2026-11-01 Kiwi: b 단독 첫 형태소가 J·E·VCP·XSV·XSA 이거나, a+b 붙인 분석에서 경계가 XSV·XSA·VCP·E — 단 STANDALONE 낱말은 띄움"""
    global _KIWI
    m = re.match(r'[가-힣]+', b)
    if not a or not m or a[-1] in ' ／': return False
    b2 = m.group(0)
    if b2 in STANDALONE: return False
    if re.fullmatch('[오아어우으요]+', b2) and re.search(r'[가-힣]$', a): return True   # 늘인 끝소리(«성급하세요／오오»)
    if b2 in JOSA and (len(b) == len(b2) or not re.match(r'[가-힣]', b[len(b2)])): return True
    if not re.search(r'[가-힣]$', a): return False
    if _KIWI is None:
        from kiwipiepy import Kiwi
        _KIWI = Kiwi()
        for n in ('시라후지', '아오', '루리', '아카', '키', '마룡'): _KIWI.add_user_word(n, 'NNP')
    a2 = re.search(r'[가-힣]+$', a).group(0); L = len(a2)
    alone = _KIWI.tokenize(b2)[0].tag
    tb = [x for x in _KIWI.tokenize(a2 + b2) if x.start == L]
    comb = tb[0].tag if tb else '-'
    return bool(re.match(r'J|E|VCP|XSV|XSA', alone) or re.match(r'XSV|XSA|VCP|E', comb))


def orphan(l):
    """한두 글자짜리 줄(부호·말줄임만 있는 줄 제외)"""
    return 0 < width(l.rstrip('」』 ')) <= 4 and not re.fullmatch(r'[…」』！？!?、。，,.\s~～☆]*', l)


def rewrap(page, maxlines, W=W, force=False):
    """한 쪽(줄바꿈 ／) → 낱말 단위로 W 이하 줄들(줄 수 최소, 고르게). 못 하면 None"""
    lines = page.split('／')
    if not force and all(width(l) <= W for l in lines): return page
    ls = [l.strip(' ') for l in lines]
    text = ls[0]
    for l in ls[1:]: text += ('​' if glue(text, l) else ' ') + l   # 붙인 자리 = 벌칙 큰 끊을 자리(다른 데서 못 끊을 때만)
    words = []; soft = set()
    for part in text.split('​'):
        words += re.findall(r'(?:@P (?=[님씨]))?(?:[^\s…]|…+(?=[…」』）！？!?、。，]|$))+…*\s*|…+\s*', part)   # «@P 님»·«@P 씨» 는 한 낱말 · 낱말 안 «…» 뒤에서도 끊을 수 있음
        soft.add(len(words))
    best = None
    N = len(words)
    from functools import lru_cache

    @lru_cache(None)
    def go(i, k):
        if i == N: return (0, ())
        if k == 0: return None
        res = None
        for j in range(i + 1, N + 1):
            l = ''.join(words[i:j]).rstrip()
            if width(l) > W: break
            sub = go(j, k - 1)
            if sub is None: continue
            c = ((W - width(l)) ** 2 + (10 ** 6 if j in soft else 0)) if j < N else (10 ** 5 if orphan(l) else 0)   # 마지막 줄 한 낱말(«있다」») 피함
            if res is None or c + sub[0] < res[0]: res = (c + sub[0], (l,) + sub[1])
        return res
    for k in range(1, maxlines + 1):
        r = go(0, k)
        if r: return '／'.join(r[1])
    return None


NAMEP = re.compile(r'^((?:@[/<])*(?:@Q\d)?[^「@{}／]{1,8}「@\.)')
EVW = 30                                                                # ★이벤트(@pW 있는 기록) 창: 이름 안 보이고 한 줄 30칸(2026-10-31 실기 «못» 한 글자 줄)


HEADANY = re.compile(r'(?:(?<=^)|(?<=／)|(?<=@[/<]))((?:@Q\d)?([^「@{}／]{0,8})「@\.)')


def nlines(t):
    """쪽 줄 수 — @K 바로 뒤 첫 ／ 는 줄을 안 차지(원문: «@K／» 뒤 4줄 쪽 15곳)"""
    return len(re.sub(r'^(?:@[/<])*／', '', t).split('／'))


def fix_layout(jp, ko):
    """쪽마다 폭 검사·다시 나눔 → (새 KO, 넘친 쪽 목록)
    ★대화창은 «이름「» 뒤 칸에 매달린 들여쓰기 — 모든 줄 폭 = 36 − 이름「 폭, 쪽이 바뀌어도(이름 안 찍혀도) 같은 기록 안에선 유지
      (2026-11-01 원문 전수 검증: 이름폭 4/6/8/10 → 둘째 줄 이후 최대 32/30/28/26, 예외는 끝 」 매달림 1건뿐)
    ★창 4줄 — 다시 나눠도 4줄 넘으면 원문처럼 «@K／» 로 쪽을 나눈다(하스피 규칙: 내용 깎지 말고 쪽 나눔)"""
    if '@pW' in jp: return fix_layout_ev(jp, ko)
    jp_pages = PAGE.split(jp); ko_pages = PAGE.split(ko)
    if len(jp_pages) != len(ko_pages): return ko, ['쪽 나눔 토큰 수 다름']
    out = []; bad = []; ind = 0
    for jpp, kop in zip(jp_pages, ko_pages):
        if PAGE.fullmatch(kop or 'x') or not kop: out.append(kop); continue
        maxl = max(nlines(jpp), 4)
        segs = []; pos = 0                                                # 쪽 안에서 이름 머리 나올 때마다 들여쓰기 바뀜
        for m in HEADANY.finditer(kop):
            segs.append((kop[pos:m.start()], ind)); ind = width(m.group(2) + '「'); segs.append((m.group(1), None)); pos = m.end()
        segs.append((kop[pos:], ind))
        def ok(t, w): return all(width(l) <= w for l in t.split('／'))
        noorph = not any(orphan(l) for t, h in segs if h is not None for l in t.split('／'))
        if all(h is None or ok(t, W - h) for t, h in segs) and nlines(kop) <= maxl and noorph: out.append(kop); continue
        if len([1 for t, h in segs if h is None]) > 1: out.append(kop); bad.append(kop); continue   # 한 쪽에 이름 둘 = 손대지 않음
        res = []
        for t, h in segs:
            if h is None or not t: res.append(t); continue
            if '@Q' in t:                                                 # 선택지 줄은 손대지 않음(넘치면 목록)
                if not ok(t, W - h): res = None; break
                res.append(t); continue
            lead = re.match(r'^(?:@[/<])*／?', t).group(0); body = t[len(lead):]
            r = body if ok(body, W - h) and not any(orphan(l) for l in body.split('／')) else rewrap(body, 99, W - h, True)
            if r is None: res = None; break
            res.append(lead + r)
        if res is None: out.append(kop); bad.append(kop); continue
        new = ''.join(res)
        if nlines(new) > maxl and '@Q' in new: out.append(kop); bad.append(kop); continue
        if nlines(new) > maxl:                                            # 4줄씩 끊어 «@K／» 로 쪽 나눔
            m = re.match(r'^(?:@[/<])*／?', new); lead = m.group(0); ls = new[len(lead):].split('／')
            n = -(-len(ls) // maxl); per = -(-len(ls) // n)               # 고르게(5줄 → 3+2)
            new = lead + '@K／'.join('／'.join(ls[i:i + per]) for i in range(0, len(ls), per))
        out.append(new)
    return ''.join(out), bad


def fix_layout_ev(jp, ko):
    """이벤트 기록: 이름 머리(「@. 까지) 떼고 30칸·쪽당 max(원문,3)줄로"""
    jp_pages = PAGE.split(jp); ko_pages = PAGE.split(ko)
    if len(jp_pages) != len(ko_pages): return ko, ['쪽 나눔 토큰 수 다름']
    out = []; bad = []
    for jpp, kop in zip(jp_pages, ko_pages):
        if PAGE.fullmatch(kop or 'x') or not kop: out.append(kop); continue
        m = NAMEP.match(kop); head = m.group(1) if m else ''
        body = kop[len(head):]
        maxl = max(len(jpp.split('／')), 3)
        if all(width(l) <= EVW for l in body.split('／')) and len(body.split('／')) <= maxl: out.append(kop); continue
        if '@Q' in body:                                                  # 선택지 줄은 일반 폭(36) 기준
            if any(width(l) > W for l in body.split('／') if '@Q' in l): bad.append(kop)
            out.append(kop); continue
        r = rewrap(body, maxl, EVW)
        if r is None: out.append(kop); bad.append(kop)
        else: out.append(head + r)
    return ''.join(out), bad


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv', 'sg_[0-9]*.tsv'))) + sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv', 'sg_sys_*.tsv'))):
        for r in csv.DictReader(open(f, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE): src[r['번호']] = r
    byjp = collections.defaultdict(list)
    for k, r in src.items(): byjp[r['JP']].append(k)
    pos = lambda w: re.sub(r'\(×\d+\)$', '', w or '')
    bypos = {pos(r['위치']): k for k, r in src.items()}
    ko = {}; how = collections.Counter(); conflict = []
    files = sorted(glob.glob(os.path.join(SRC, '*.tsv')))
    newfmt = lambda f: 'sg_miss_' in f
    sysf = lambda f: 'sg_sys_' in f                                       # 시스템 문자열 번역은 옛 판(번호 밀림) — 위치(파일:16진) 로
    for f in files:
        for r in csv.DictReader(open(f, encoding='utf-8-sig'), delimiter='\t', quoting=csv.QUOTE_NONE):
            kv = (r.get('KO') or '').strip()
            if not kv: how['빈 KO'] += 1; continue
            if sysf(f):
                ks = [k for k, s in src.items() if k.startswith('S') and s['위치'] == r['위치'] and s['JP'] == r['JP']]
                if not ks: ks = [k for k in byjp.get(r['JP'], []) if k.startswith('S')]
                if not ks: how['시스템 못 맞춤'] += 1; continue
                how['시스템 위치 일치'] += 1
            elif newfmt(f):
                k = r['번호']
                if k not in src or src[k]['JP'] != r['JP']: how['새 판 번호·원문 불일치'] += 1; continue
                ks = [k]; how['새 판 번호'] += 1
            else:
                ks = byjp.get(r['JP'])
                if ks: how['원문 일치'] += 1
                elif pos(r['위치']) in bypos: ks = [bypos[pos(r['위치'])]]; how['위치 일치'] += 1
                else: how['못 맞춤'] += 1; continue
            for k in ks:
                if k in ko and ko[k] != kv: conflict.append((k, ko[k], kv))
                ko.setdefault(k, kv)
    print('맞추기', dict(how), '· 서로 다른 번역 충돌', len(conflict))
    miss = [k for k in src if k not in ko]
    print('번역 %d / %d · 빠짐 %d %s' % (len(ko), len(src), len(miss), miss[:10]))
    # 통일·토큰·폭
    fixes = collections.defaultdict(list)                                # 넘침 고친 안(하스피 확인) work/text/ko_fix.tsv: 번호·전·후
    fp = os.path.join(ROOT, 'work', 'text', 'ko_fix.tsv')
    if os.path.exists(fp):
        for r in csv.DictReader(open(fp, encoding='utf-8'), delimiter='	', quoting=csv.QUOTE_NONE): fixes[r['번호']].append((r['전'], r['후']))
    choice = {}                                                          # 선택지 줄임(하스피 2026-10-31 «적당히 줄여도»): work/text/ko_choice.tsv 전→후, 모든 줄에
    cp = os.path.join(ROOT, 'work', 'text', 'ko_choice.tsv')
    if os.path.exists(cp):
        for r in csv.DictReader(open(cp, encoding='utf-8'), delimiter='	', quoting=csv.QUOTE_NONE): choice[r['전']] = r['후']
    final = {}; toks = []; over = []; changed = collections.Counter()
    for k, v in ko.items():
        jp = src[k]['JP']; u = unify(v, not k.startswith('S'))
        for x, y in fixes.get(k, []):
            if x not in u: sys.exit('⛔ ko_fix 의 «전» 이 번역에 없음 %s %s' % (k, x))
            u = u.replace(x, y); changed['넘침 줄임'] += 1
        if u != v: changed['이름·호칭 통일'] += 1
        for x, y in choice.items():
            if x in u: u = u.replace(x, y); changed['선택지 줄임'] += 1
        if TOK.findall(u) != TOK.findall(jp): toks.append(k)
        if k.startswith('S'):
            if '.' not in jp: u = re.sub(r'\.(?=@K|／|@R|」|$)', '', u)        # 반각 마침표(글꼴 없음) — 시스템 문장 끝은 빼기(바이트 예산)
            for h, f in (('?', '？'), ('!', '！'), (',', '，'), ('(', '（'), (')', '）'), ('+', '＋')):          # 반각 ? ! , 는 원문이 반각을 안 쓴 문자열에선 게임이 못 찍음(실기 «괜찮을까요▒») → 전각
                if h in u and h not in jp: u = u.replace(h, f); changed['시스템 전각 부호'] += 1
            final[k] = u; continue
        lay, bad = fix_layout(jp, u)
        if lay != u: changed['줄 다시 나눔'] += 1
        if bad: over.append((k, bad))
        final[k] = lay
    print('바뀜', dict(changed), '· 토큰 다름', len(toks), '· 넘침', len(over))
    T = os.path.join(ROOT, 'work', 'text')
    with open(os.path.join(T, 'ko_script.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\tJP\tKO\n')
        for k in src:
            if not k.startswith('S') and k in final: o.write('%s\t%s\t%s\n' % (k, src[k]['JP'], final[k]))
    with open(os.path.join(T, 'ko_sys.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t위치\tJP\tKO\n')
        for k in src:
            if k.startswith('S') and k in final: o.write('%s\t%s\t%s\t%s\n' % (k, src[k]['위치'], src[k]['JP'], final[k]))
    with open(os.path.join(T, 'merge_issues.txt'), 'w', encoding='utf-8') as o:
        o.write('== 토큰 다름 %d\n' % len(toks))
        for k in toks: o.write('[%s]\n JP %s\n KO %s\n JP토큰 %s\n KO토큰 %s\n' % (k, src[k]['JP'], ko[k], TOK.findall(src[k]['JP']), TOK.findall(ko[k])))
        o.write('\n== 넘침 %d\n' % len(over))
        for k, b in over: o.write('[%s] %s\n' % (k, ' ‖ '.join(b)))
        o.write('\n== 충돌 %d\n' % len(conflict))
        for k, a, b in conflict: o.write('[%s]\n 앞 %s\n 뒤 %s\n' % (k, a, b))
    return src, ko, final


if __name__ == '__main__':
    main()
