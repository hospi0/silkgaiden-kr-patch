# -*- coding: utf-8 -*-
r"""PoC(2026-10-31) — 스테이트 5 «泉の精「じゃ、あたしは／これで失礼するわね」» → 한글, MFOUN·MSAV 4곳
  글자 번호 규칙(SUGOBEN 0x0602B5C6~, 실크와 같음): 히라가나 JIS−0x23F9 · 가타카나 JIS−0x2481 · 0x2000~6 표 · 한자·기호 = 큰 표(SUGOBEN 0x48048, (JIS,번호) 1,246쌍 이진 탐색)
  → «어디에도 안 쓰이는» 큰 표 한자 코드에 한글을 배정하고 FONT.DAT(16×12 1비트, 24 B) 그 번호 칸만 갈무리11 한글로
  ARC.AKV: 파일 2048 정렬 — 바뀐 파일이 다음 파일 전까지 들어가면 제자리, ARC.IND 크기만 고침
  python tools/poc.py → work/build/ARC.AKV·ARC.IND"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import akv

ARC = os.path.join(ROOT, 'work', 'arc')
BIG, NBIG = 0x48048, 1246
FULL = 64                                   # 전각 글자 번호 n = FONT.DAT n+64 칸(0x0606F900 = [0x2D3A00 반각, 0x2D4000 = +0x600 전각])
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'
PUNCT = ',.!?:;~、。，．！？：；…'
TR = {'泉の精「@.じゃ、あたしは\nこれで失礼するわね」': '샘의 정령「@.그럼, 나는\n이만 실례할게」'}
PUNCT_GLYPH = {',': {(2, 8), (3, 8), (2, 9), (3, 9), (3, 10), (2, 11)}}   # 실크 insert.py 와 같음


def sjis_of_jis(j):
    hi, lo = j >> 8, j & 0xFF
    s1 = (hi + 1) // 2 + (0x70 if hi <= 0x5E else 0xB0)
    s2 = lo + (0x1F if hi % 2 else 0x7E) + (1 if hi % 2 and lo >= 0x60 else 0)
    return bytes([s1, s2])


def big_table():
    d = open(os.path.join(ARC, 'SUGOBEN'), 'rb').read()
    return [struct.unpack_from('>HH', d, BIG + 4 * i) for i in range(NBIG)]


def used_chars():
    """쓰이는 글자 = 대본 파일 전부(통째로 cp932) + 코드 파일 문자열(extract.sys_strings) — 프로그램 이진 자료는 빼야 함(1바이트씩 훑으면 모든 한자가 걸림)"""
    import extract
    used = set()
    for f in extract.script_files():
        used |= set(open(os.path.join(ARC, f), 'rb').read().decode('cp932'))
    for f in extract.SYS_FILES():
        for a, s in extract.sys_strings(open(os.path.join(ARC, f), 'rb').read()): used |= set(s)
    return used


def hangul_glyph(ch, _g={}):
    if ch in PUNCT_GLYPH:
        rows = [0] * 12
        for x, y in PUNCT_GLYPH[ch]: rows[y] |= 0x8000 >> x
        return b''.join(struct.pack('>H', r) for r in rows)
    if not _g:
        import bdf
        _g['f'] = bdf.Font(GALMURI)
        _g['top'] = min(y for c in '가각힣맑앙' for x, y in _g['f'].draw(c)[0])
    pts, w = _g['f'].draw(ch)
    rows = [0] * 12
    for x, y in pts:
        yy = y - _g['top'] + 1
        assert 0 <= yy < 12 and 0 <= x < 12, ('글자 칸 밖', ch, x, yy)
        rows[yy] |= 0x8000 >> x
    return b''.join(struct.pack('>H', r) for r in rows)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    used = used_chars()
    free = [(j, n) for j, n in big_table() if j >= 0x3021 and sjis_of_jis(j).decode('cp932') not in used]
    print('큰 표 한자 중 안 쓰이는 코드', len(free))
    tr = {k: re.sub('([%s]) +' % re.escape(PUNCT), r'\1', v) for k, v in TR.items()}
    need = sorted({c for v in tr.values() for c in v if '가' <= c <= '힣' or c in PUNCT_GLYPH})
    assert len(need) <= len(free)
    amap = {c: free[i] for i, c in enumerate(need)}
    fnt = bytearray(open(os.path.join(ARC, 'FONT.DAT'), 'rb').read())
    for c, (j, n) in amap.items(): fnt[24 * (FULL + n):24 * (FULL + n) + 24] = hangul_glyph(c)
    def enc(s):
        out = b''
        for c in s:
            if c in amap: out += sjis_of_jis(amap[c][0])
            elif c == ' ': out += '　'.encode('cp932')
            else: out += c.encode('cp932')
        return out
    new = {'FONT.DAT': bytes(fnt)}
    for f in ('MFOUN', 'MSAV'):
        d = open(os.path.join(ARC, f), 'rb').read(); n = 0
        for jp, ko in tr.items():
            n += d.count(jp.encode('cp932')); d = d.replace(jp.encode('cp932'), enc(ko))
        new[f] = d; print(f, '바꾼 곳', n, len(d), 'B')
    ind = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'ARC.IND'), 'rb').read())
    a = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'ARC.AKV'), 'rb').read())
    ix = akv.index(bytes(ind)); starts = sorted(o for _, o, _ in ix) + [len(a)]
    for k, (nm, o, s) in enumerate(ix):
        if nm not in new: continue
        nxt = min(x for x in starts if x > o)
        assert o + len(new[nm]) <= nxt, ('칸 넘침', nm)
        a[o:o + max(s, len(new[nm]))] = new[nm] + bytes(max(0, s - len(new[nm])))
        struct.pack_into('>I', ind, 20 * k + 16, len(new[nm]))
    out = os.path.join(ROOT, 'work', 'build'); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'ARC.AKV'), 'wb').write(a); open(os.path.join(out, 'ARC.IND'), 'wb').write(ind)
    print('한글 배정', {c: '%s→%d' % (sjis_of_jis(j).decode('cp932'), n) for c, (j, n) in amap.items()})


if __name__ == '__main__':
    main()
