# -*- coding: utf-8 -*-
r"""드래곤 마스터 실크 외전 넣기 빌더(2026-10-31) — 번역 TSV + 그림 → work/build/(ARC.AKV·ARC.IND·0)
  번역: my files/tsv/sg_###.tsv(대본 본문, JP 표시 그대로 맞춰 찾음) · sg_sys_###.tsv(코드 문자열, 위치 = 파일:16진(바이트))
    KO 빈칸 = 원문 그대로 · ★쓰는 순간 막음: 토큰({n}·@코드·%s·／ 개수와 차례) · 시스템 문자열 바이트 예산 · 글꼴에 없는 글자
    문장부호 뒤 공백 지움. 한글 문장 부호: ! ? , ~ → ！？，～(글꼴 전각) · . → 새 칸에 그림 · 공백·영대문자·숫자·/ % 는 반각 그대로
  글꼴: 글자 번호 규칙(실크와 같음) 히라 JIS−0x23F9 · 가타 JIS−0x2481 · 큰 표(SUGOBEN 0x48048 (JIS,번호) 1,246쌍) · 전각 번호 n = FONT.DAT n+64 칸
    → 최종 문장에 «안 쓰이는» 큰 표 코드(한자 먼저, 그다음 기호) → 그다음 안 쓰이는 히라·가타 코드 에 한글·새 부호를 배정, 그 칸 그림만 갈무리11
  대본(M*): 기록(NUL 끊김) 머리 그대로 + 본문 바꿔 다시 이음(포인터 없음, 길이 자유)
  이름 입력: tools/nameentry.patch(XCHK) — 음절 110 도 같은 배정
  그림: work/build/arc/*(gfx_plates·gfx_misc 결과) 를 같은 이름 ARC 항목으로
  ARC.AKV: 바뀐 파일이 제 칸(2048 정렬, 다음 파일 전)에 들어가면 제자리 · 아니면 전체를 2048 정렬로 촘촘히 다시 묶음(AKV 크기 안) · ARC.IND 위치·크기 고침
  python tools/build.py [--test]   (--test = 번역 대신 가나→한글 시험 번역, work/build_test 로)"""
import csv, glob, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import akv, extract, nameentry, poc

ARC = os.path.join(ROOT, 'work', 'arc')
TSV = os.path.join(ROOT, 'my files', 'tsv')
FULL = 64
PUNCT = ',.!?~:;…、。，．！？：；～'
TO_FULL = {'!': '！', '?': '？', ',': '，', '~': '～', '.': '．'}
DRAW = {'．'}                                                            # 글꼴에 없어 새 칸에 그리는 부호(전각 마침표 — 큰 표에 없음). ★반각 . 은 제어 코드(@.·%2.2s)라 절대 안 건드림
PERIOD = {(2, 10), (3, 10), (2, 11), (3, 11)}                             # 16×12 칸 왼쪽 아래 2×2 점
HANGUL = re.compile('[가-힣]')
SHORT = re.compile(r'@\.|@K|@P|@B|@C|@Q\d|@\}|@=|@<|@/|@pW|@F\d?|@\(|@\+|%[-0-9]*[dsx]|／|\{\d+\}')


def jis(sj):
    b = sj.encode('cp932'); s1, s2 = b[0], b[1]
    hi = (s1 - (0x70 if s1 < 0xA0 else 0xB0)) * 2 - (1 if s2 < 0x9F else 0)
    lo = s2 - (0x1F if s2 < 0x7F else 0x20) if s2 < 0x9F else s2 - 0x7E
    return hi << 8 | lo


def tokens(s):
    return SHORT.findall(s)


def tokens_noline(s):
    """대본: 줄바꿈 ／ 는 번역에서 달라도 됨(2026-10-31 — 줄 폭 36·쪽당 줄 수는 tools/merge_ko.py 가 검사)"""
    return [x for x in SHORT.findall(s) if x != '／']


def tokens_match_script(ko, jp):
    """대본 토큰 비교 — ／ 무시 + 번역에서 «더 넣은 @K»(merge_ko 쪽 나눔, 2026-11-01) 허용, 나머지 차례는 그대로"""
    a = tokens_noline(ko); b = tokens_noline(jp); j = 0
    for x in a:
        if j < len(b) and x == b[j]: j += 1
        elif x == '@K': continue
        else: return False
    return j == len(b)


def squeeze(s):
    return re.sub('([%s]) +' % re.escape(PUNCT), r'\1', s)


def load_tr(test=False):
    """대본: JP표시 → KO표시 · 시스템: (파일, 위치) → KO"""
    scr, sysr = {}, {}
    if test:
        # 시험 번역: 일본 글자(가나·한자) 하나하나를 실크 본편 번역 음절 986자 안의 한글로(실제 번역 규모의 칸 배정·예산·묶기 검산)
        pool = sorted(set(re.findall('[가-힣]', ''.join(open(f, encoding='utf-8').read() for f in glob.glob(r'C:\claude\project\dragonmastersilk-kr-patch\data\번역\*.tsv')))))
        jp = re.compile('[ぁ-んァ-ヶ一-龠々]')
        tr = lambda s: jp.sub(lambda m: pool[(ord(m.group(0)) * 7919) % len(pool)], s)
        for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'script.tsv'), encoding='utf-8'), delimiter='	', quoting=csv.QUOTE_NONE):
            scr[r['JP']] = tr(r['JP'])
        for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'sys.tsv'), encoding='utf-8'), delimiter='	', quoting=csv.QUOTE_NONE):
            sysr[(os.path.basename(r['파일']), int(r['위치'], 16))] = (r['JP'], tr(r['JP']))
        return scr, sysr
    T = os.path.join(ROOT, 'work', 'text')                              # 2026-10-31: 하스피 번역 병합본(tools/merge_ko.py)
    for r in csv.DictReader(open(os.path.join(T, 'ko_script.tsv'), encoding='utf-8'), delimiter='	', quoting=csv.QUOTE_NONE):
        if (r.get('KO') or '').strip(): scr[r['JP']] = r['KO'].strip()
    for p in [os.path.join(T, 'ko_sys.tsv'), os.path.join(T, 'ko_sys_extra.tsv')]:   # extra = 추출이 거른 일본어 한 글자 문자열(프로필 %2dつ·%2d枚 등, 2026-10-31 실기)
        for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
            if (r.get('KO') or '').strip():
                m = re.match(r'(.+):([0-9A-F]+)\(\d+B\)', r['위치']); sysr[(m.group(1), int(m.group(2), 16))] = (r['JP'], r['KO'].strip(' \r\n'))   # 앞 전각 공백 살림(파이썬 strip 은 U+3000 도 지움)
    return scr, sysr


def koize(s, full=True):
    """한글 번역 문장 다듬기: 부호 뒤 공백 지움 · 반각 ! ? , ~ → 전각(대본만 — 시스템 문자열은 원문도 반각 부호를 써서 그대로, 바이트 예산)"""
    s = squeeze(s)
    if not full: return s
    out = []; k = 0
    for m in SHORT.finditer(s):                                           # 제어 코드(@. %2.2s {n} …) 밖에서만 바꿈
        out.append(''.join(TO_FULL.get(c, c) for c in s[k:m.start()])); out.append(m.group(0)); k = m.end()
    out.append(''.join(TO_FULL.get(c, c) for c in s[k:]))
    return ''.join(out)


class Enc:
    def __init__(self, need, used):
        big = poc.big_table()
        cand = [j for j, n in big if j >= 0x3021] + [j for j, n in big if j < 0x3021]
        cand += list(range(0x2421, 0x2474)) + list(range(0x2521, 0x2577))
        cand = [j for j in cand if poc.sjis_of_jis(j).decode('cp932') not in used]
        if len(need) > len(cand): raise SystemExit('⛔ 글꼴 칸 모자람: 필요 %d · 빈 칸 %d — 표·FONT.DAT 늘리기 판단 필요' % (len(need), len(cand)))
        num = {j: n for j, n in big}
        self.map = {}
        for c, j in zip(need, cand):
            n = num[j] if j in num else (j - 0x23F9 if j < 0x2500 else j - 0x2481)
            self.map[c] = (j, n)
        self.free = len(cand) - len(need)

    def enc(self, s):
        out = b''
        for c in s:
            if c in self.map: out += poc.sjis_of_jis(self.map[c][0])
            else: out += c.encode('cp932')
        return out

    def font(self, fnt):
        fnt = bytearray(fnt)
        for c, (j, n) in self.map.items():
            if c in DRAW:
                rows = [0] * 12
                for x, y in PERIOD: rows[y] |= 0x8000 >> x
                g = b''.join(struct.pack('>H', r) for r in rows)
            else: g = poc.hangul_glyph(c)
            fnt[24 * (FULL + n):24 * (FULL + n) + 24] = g
        return bytes(fnt)


BASE = {'SUGOBEN': 0x06026540, 'XDEB1': 0x060A0000}                    # 램 적재 주소(SUGOBEN = 글자 번호 코드 디스어셈 · XDEB1 = 문자열 포인터 88개 일치, 2026-11-01)


def relocate(over, sysfin, new, E):
    """예산 넘친 시스템 문자열 → 같은 파일에서 «번역이 짧아 남는 칸»(다른 문자열의 KO+NUL 뒤 ~ 원문 끝)에 쓰고, 그 문자열을 가리키는 u32 포인터를 고친다.
    ★포인터가 1개 이상 있고, 쓸 자리 안을 가리키는 포인터가 없을 때만. 못 하면 over 에 남김"""
    left = []; taken = {}
    for fn, off, lj, lk, ko in over:
        if fn not in BASE: left.append((fn, off, lj, lk, ko)); continue
        d = bytearray(new.get(fn) or open(os.path.join(ARC, fn), 'rb').read()); base = BASE[fn]
        kb = E.enc(ko) + b'\0'
        ptrs = [i for i in range(0, len(d) - 3, 2) if struct.unpack_from('>I', d, i)[0] == base + off]
        if not ptrs: left.append((fn, off, lj, lk, ko)); continue
        host = None
        for hf in dict.fromkeys((fn, 'SUGOBEN')):                          # 같은 파일 → 없으면 늘 상주하는 본체 SUGOBEN
            h = d if hf == fn else bytearray(new.get(hf) or open(os.path.join(ARC, hf), 'rb').read()); hb = BASE[hf]
            vals = set(struct.unpack_from('>I', h, i)[0] for i in range(0, len(h) - 3, 2))
            for (f2, o2), (jp2, ko2) in sorted(sysfin.items()):
                if f2 != hf or (hf == fn and o2 == off): continue
                end = o2 + len(jp2.replace('／', '\n').encode('cp932'))
                a = taken.get((hf, o2), o2 + len(E.enc(ko2)) + 1)           # 이미 옮겨 넣은 문자열이 있으면 그 뒤
                if a + len(kb) <= end and all(h[x] == 0 for x in range(a, a + len(kb))) and \
                   not any(hb + a <= v < hb + a + len(kb) for v in vals):
                    host = (hf, h, a); taken[(hf, o2)] = a + len(kb); break
            if host: break
        if host is None: left.append((fn, off, lj, lk, ko)); continue
        hf, h, a = host
        h[a:a + len(kb)] = kb
        if h is not d: new[hf] = bytes(h)
        d[off:off + lj] = bytes(lj)                                       # 옛 자리는 아무도 안 가리킴 → 0
        for i in ptrs: struct.pack_into('>I', d, i, BASE[hf] + a)
        new[fn] = bytes(d)
        print('  옮김 %s:%X → %s:%X (%s, 포인터 %s)' % (fn, off, hf, a, ko, ' '.join('%X' % i for i in ptrs)))
    return left


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    test = '--test' in sys.argv
    out = os.path.join(ROOT, 'work', 'build_test' if test else 'build'); os.makedirs(out, exist_ok=True)
    scr, sysr = load_tr(test)
    err = []
    # 1) 대본 최종 문장
    files = {}
    for f in extract.script_files():
        recs = []
        for k, o, s in extract.records(f):
            head, body = extract.split_record(s)
            if not extract.JP.search(body): recs.append(s); continue
            disp, toks = extract.show(body)
            if disp in scr:
                ko = koize(scr[disp])
                if not tokens_match_script(ko, disp): err.append('토큰 %s:%d\n  JP %s\n  KO %s' % (f, k, tokens(disp), tokens(ko))); recs.append(s); continue
                recs.append(head + extract.unshow(ko, toks))
            else: recs.append(s)
        files[f] = recs
    # 2) 시스템 문자열 최종
    sysfin = {}
    for (fn, off), (jp, ko) in sysr.items():
        ko = koize(ko, full=False)
        msg = '@K' in jp and tokens_noline(ko) == tokens_noline(jp)          # 대화창 메시지(@K)는 ／ 개수 달라도 됨 — 원문이 자동 줄바꿈에 맡긴 문장(2026-11-01 꽉 찬 줄 뒤 빈 줄)
        if tokens(ko) != tokens(jp) and not msg: err.append('토큰 %s:%X JP %s KO %s' % (fn, off, tokens(jp), tokens(ko))); continue
        sysfin[(fn, off)] = (jp, ko.replace('／', '\n'))
    if err: raise SystemExit('⛔ 토큰 다름 %d\n' % len(err) + '\n'.join(err[:20]))
    # 3) 글꼴 배정 — 쓰이는 일본 글자(최종) 빼고, 한글·새 부호를 배정
    used = set()
    for recs in files.values():
        for s in recs: used |= set(s)
    for f in extract.SYS_FILES():
        for a, t in extract.sys_strings(open(os.path.join(ARC, f), 'rb').read()):
            fn = os.path.basename(f)
            used |= set(sysfin[(fn, a)][1] if (fn, a) in sysfin else t)
    used |= set('・－～☆゛゜')                                               # 이름판에 남는 글자
    need_chars = set()
    for s in used:
        if HANGUL.match(s) or s in DRAW: need_chars.add(s)
    need_chars |= set(nameentry.SYL) | set('다음이전')
    need = sorted(need_chars)
    if '--debug' in sys.argv:
        import collections
        left = collections.Counter(c for c in used if re.match('[ぁ-んァ-ヶ一-龠]', c)); print('남은 일본 글자', len(left), ''.join(sorted(left))[:300])
    E = Enc(need, used)
    print('글꼴 배정: 한글·부호 %d · 남는 칸 %d' % (len(need), E.free))
    # 4) 파일 만들기
    new = {}
    for f, recs in files.items():
        b = b'\0'.join(E.enc(s) for s in recs)
        orig = open(os.path.join(ARC, f), 'rb').read()
        if b != orig: new[f] = b
    over = []
    for (fn, off), (jp, ko) in sysfin.items():
        key = fn if fn != '0' else '../disc0/0'
        d = bytearray(new.get(key) or open(os.path.join(ARC, key), 'rb').read())
        jb = jp.replace('／', '\n').encode('cp932'); kb = E.enc(ko)
        assert d[off:off + len(jb)] == jb, ('원문 자리 다름', fn, hex(off))
        if len(kb) > len(jb): over.append((fn, off, len(jb), len(kb), ko)); continue
        d[off:off + len(jb)] = kb + bytes(len(jb) - len(kb)); new[key] = bytes(d)
    over = relocate(over, sysfin, new, E)                                  # 예산 넘는 짧은 이름(白藤→시라후지) = 같은 파일 남는 칸으로 옮기고 포인터 고침
    if over: raise SystemExit('⛔ 시스템 문자열 예산 넘침 %d\n' % len(over) + '\n'.join('%s:%X %d→%d %s' % o for o in over[:30]))
    new['XCHK'] = nameentry.patch(new.get('XCHK') or open(os.path.join(ARC, 'XCHK'), 'rb').read(), E.enc)
    new['FONT.DAT'] = E.font(open(os.path.join(ARC, 'FONT.DAT'), 'rb').read())
    for p in glob.glob(os.path.join(ROOT, 'work', 'gfx_out', '*')):
        nm = os.path.basename(p); new[nm] = open(p, 'rb').read()
    # 5) ARC 다시 묶기
    ind = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'ARC.IND'), 'rb').read())
    a = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'ARC.AKV'), 'rb').read()); AK = len(a)
    ix = akv.index(bytes(ind)); order = sorted(range(len(ix)), key=lambda k: ix[k][1])
    inplace = all(ix[k][0] not in new or ix[k][1] + len(new[ix[k][0]]) <= (ix[order[i + 1]][1] if i + 1 < len(order) else AK)
                  for i, k in enumerate(order))
    if inplace:
        for k, (nm, o, s) in enumerate(ix):
            if nm in new:
                a[o:o + max(s, len(new[nm]))] = new[nm] + bytes(max(0, s - len(new[nm])))
                struct.pack_into('>I', ind, 20 * k + 16, len(new[nm]))
        how = '제자리'
    else:
        body = bytearray(); pos = {}
        for k in order:
            nm, o, s = ix[k]; data = new.get(nm, bytes(a[o:o + s]))
            pos[k] = (len(body), len(data)); body += data + bytes((-len(data)) % 2048)
        if len(body) > AK: raise SystemExit('⛔ ARC.AKV 넘침 %d > %d' % (len(body), AK))
        a = body + bytes(AK - len(body))
        for k, (o, s) in pos.items(): struct.pack_into('>II', ind, 20 * k + 12, o, s)
        how = '다시 묶음(끝 여유 %d B)' % (AK - len(body))
    open(os.path.join(out, 'ARC.AKV'), 'wb').write(a); open(os.path.join(out, 'ARC.IND'), 'wb').write(ind)
    if '../disc0/0' in new: open(os.path.join(out, '0'), 'wb').write(new['../disc0/0'])
    # 6) 되읽기 검산: IND 대로 꺼낸 파일 = new
    ix2 = akv.index(bytes(ind)); bad = [nm for nm, o, s in ix2 if nm in new and bytes(a[o:o + s]) != new[nm]]
    assert not bad, bad
    print('대본 번역 %d · 시스템 %d · 바뀐 ARC 파일 %d · ARC %s · 검산 OK → %s' % (sum(1 for f in files for s in files[f]) if False else len(scr), len(sysfin), len(new), how, out))


if __name__ == '__main__':
    main()
