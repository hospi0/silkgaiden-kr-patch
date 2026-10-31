# -*- coding: utf-8 -*-
r"""대사 추출(2026-10-31) — work/arc 의 대본 파일(M*: 순수 대본, NUL 로 끊긴 기록 · «=라벨» 구간 · «E» 끝)과 코드 파일 문자열
  대본 기록 = 머리(HEAD: 16진 3자리 · @m · @{얼굴⏎ · @F · @p|음성|) + 본문 — 본문만 번역, 머리는 그대로
  본문 표시: 줄바꿈 ⏎ → ／ · 긴 제어(LONG)는 {1}{2}… 번호 토큰(차례대로 원래 값으로 복원) · 짧은 제어(@K @P @. @Q1 @} @= @< @/ @B @pW @F)는 그대로
  코드 파일(SUGOBEN·X*·/0) = textscan 문자열(NUL 끝, 제자리 — 예산 = 원래 바이트)
  → work/text/script.tsv(ID·같은글·JP·토큰) · work/text/sys.tsv(파일·위치·바이트·JP)
  python tools/extract.py"""
import os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import textscan

ARC = os.path.join(ROOT, 'work', 'arc')
HEAD = re.compile(r'^[0-9a-f]{3}(?:@m\d+)?(?:@\{[^\n]*\n)?(?:@F\d?)?(?:@p\|[^|]*\|)?')
LONG = re.compile(r'@p\|[^|]*\||@\{[^\n]*\n|@\([^\n]*\n|@R\{\d+\}|@K\{\d+\}|@m\d+')
JP = re.compile(r'[ぁ-んァ-ヶ一-龠]')


def is_script(d):
    return not any(b < 0x20 and b not in (0, 10) for b in d)


def script_files():
    return sorted(f for f in os.listdir(ARC) if f.startswith('M') and '.' not in f and is_script(open(os.path.join(ARC, f), 'rb').read()))


def split_record(s):
    """기록 → (머리, 본문) — 「=라벨⏎」로 시작하는 기록은 라벨 줄까지 머리(그 뒤에 대사가 바로 이어짐: 2026-10-31 통째로 건너뛰어 구간 첫 대사가 빠졌었음)"""
    pre = ''
    if s.startswith('=') and '\n' in s:
        i = s.index('\n') + 1; pre, s = s[:i], s[i:]
    m = HEAD.match(s)
    return (pre + s[:m.end()], s[m.end():]) if m else (pre, s)


def show(body):
    """본문 → (표시 문자열, 긴 토큰 목록)"""
    toks = []
    def rep(m):
        toks.append(m.group(0)); return '{%d}' % len(toks)
    return LONG.sub(rep, body).replace('\n', '／'), toks


def unshow(disp, toks):
    s = disp.replace('／', '\n')
    return re.sub(r'\{(\d+)\}', lambda m: toks[int(m.group(1)) - 1], s)


def records(f):
    d = open(os.path.join(ARC, f), 'rb').read(); o = 0
    for k, p in enumerate(d.split(b'\0')):
        yield k, o, p.decode('cp932'); o += len(p) + 1


SYSPAT = re.compile(rb'(?:[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]|[\x20-\x7e]|\x0a)+(?=\x00)')


def sys_strings(d):
    """코드 파일 문자열 — NUL 끝 SJIS·ASCII 덩어리마다 시작 = 덩어리 처음(앞이 NUL 이면) 아니면 덩어리 안 첫 4바이트 정렬 자리
       (앞 자료 바이트가 SJIS 첫 바이트처럼 보여 «激Rンピューター» 로 붙는 것 막기) · 전각 일본어 2자 이상(한자만 있는 메뉴 낱말 포함)"""
    for m in SYSPAT.finditer(d):
        s, e = m.start(), m.end()
        starts = [s] if (s == 0 or d[s - 1] == 0) else [a for a in range((s + 3) & ~3, e, 4)]
        for a in starts:
            try: t = d[a:e].decode('cp932')
            except UnicodeDecodeError: continue
            jp = re.findall(r'[ぁ-んァ-ヶ一-龠ー々〆]', t)
            u = re.sub(r'@[A-Za-z]|@[.}=<>/(+]|\{\d+\}|%[-0-9]*[dsx]', '', t).replace('_', '')   # ★제어 코드는 비율에서 뺌(2026-11-01 «@>@Cの勝ち@K{60}»·«データ%d %s面…» 빠졌음)
            if len(jp) >= 2 and len(re.findall(r'[!-~]', u)) <= len(u.replace(' ', '')) * 0.6:   # _·공백 = 메뉴 간격(_情____報)
                yield a, t; break                                         # 맞는 시작을 찾을 때까지 다음 정렬 자리(2026-10-31: 첫 자리만 보고 멈춰 기본 이름 10개 빠졌음)


SYS_FILES = lambda: [f for f in sorted(os.listdir(ARC)) if f == 'SUGOBEN' or (f.startswith('X') and '.' not in f)] + ['../disc0/0']


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = []; first = {}; chars = 0; uniq_chars = 0
    for f in script_files():
        for k, o, s in records(f):
            head, body = split_record(s)
            if not JP.search(body): continue
            disp, toks = show(body)
            assert unshow(disp, toks) == body
            mid = '%s:%d' % (f, k)
            n = len(JP.findall(body)); chars += n
            dup = first.get(disp, '')
            if not dup: first[disp] = mid; uniq_chars += n
            rows.append((mid, dup, disp, '\x1f'.join(toks)))
    with open(os.path.join(ROOT, 'work', 'text', 'script.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('ID\t같은글\tJP\t토큰\n')
        for r in rows: o.write('\t'.join(x.replace('\t', ' ').replace('\n', '\\n') for x in r) + '\n')   # 토큰 안 줄바꿈 → \n 글자(2026-10-31: 행이 쪼개져 번역 TSV 392행 깨졌었음)
    sysr = []
    for f in SYS_FILES():
        d = open(os.path.join(ARC, f), 'rb').read()
        for off, t in sys_strings(d):
            sysr.append((os.path.basename(f), off, len(t.encode('cp932')), t.replace('\n', '／')))
    with open(os.path.join(ROOT, 'work', 'text', 'sys.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('파일\t위치\t바이트\tJP\n')
        for r in sysr: o.write('%s\t%X\t%d\t%s\n' % r)
    print('대본 파일 %d · 기록 %d (같은 글 빼면 %d) · 글자 %d (같은 글 빼면 %d)' % (len(script_files()), len(rows), len(first), chars, uniq_chars))
    print('코드 파일 문자열 %d · %s' % (len(sysr), dict(collections.Counter(r[0] for r in sysr).most_common(12))))


if __name__ == '__main__':
    main()
