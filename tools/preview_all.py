# -*- coding: utf-8 -*-
r"""그림 한글화 미리보기 모음(2026-10-31) → my files/그림미리보기/NN_이름.png — 위 원본 · 아래 한글(3배, 실제 팔레트)
  BG8·S8 = 파일 안 팔레트 · 이름표(MONNAM·MAONAM·SYSTEM.DAT·XCHK.BIN) = 전투 스테이트 30 CRAM(0번·0x600번 뱅크)
  python tools/preview_all.py"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import bg8, gfx_misc as M
ARC = os.path.join(ROOT, 'work', 'arc'); NEW = os.path.join(ROOT, 'work', 'gfx_out')
OUT = os.path.join(ROOT, 'my files', '그림미리보기')
LAB = ImageFont.truetype(os.path.join('C:' + os.sep, 'Windows', 'Fonts', 'malgunbd.ttf'), 18)


def cram(bank):
    c = open(os.path.join(ROOT, 'work', 'mem', 's30', 'CRAM.bin'), 'rb').read()
    return [((w & 31) * 8, ((w >> 5) & 31) * 8, ((w >> 10) & 31) * 8) for w in (struct.unpack_from('<H', c, 2 * (bank + k))[0] for k in range(256))]


def img(a, p, k=3):
    return Image.fromarray(np.array([[p[v] for v in r] for r in a], dtype=np.uint8)).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)


def sheet(name, title, pairs, k=3):
    """pairs = [(설명, 원본 배열, 새 배열, 팔레트)] → 줄마다 원본|한글"""
    rows = []
    for cap, a, b, p in pairs:
        ia, ib = img(a, p, k), img(b, p, k)
        w = ia.width * 2 + 30; h = ia.height + 28
        im = Image.new('RGB', (w, h), (36, 36, 44)); d = ImageDraw.Draw(im)
        d.text((4, 2), cap + '   (왼쪽 원본 · 오른쪽 한글)', font=LAB, fill=(255, 220, 80))
        im.paste(ia, (0, 26)); im.paste(ib, (ia.width + 30, 26)); rows.append(im)
    W = max(r.width for r in rows); H = sum(r.height + 8 for r in rows) + 40
    S = Image.new('RGB', (W, H), (24, 24, 30)); d = ImageDraw.Draw(S)
    d.text((6, 6), title, font=ImageFont.truetype(os.path.join('C:' + os.sep, 'Windows', 'Fonts', 'malgunbd.ttf'), 24), fill=(255, 255, 255))
    y = 40
    for r in rows: S.paste(r, (0, y)); y += r.height + 8
    S.save(os.path.join(OUT, name + '.png')); print(name, S.size)


def bgpair(fn, box):
    d0 = open(os.path.join(ARC, fn), 'rb').read(); d1 = open(os.path.join(NEW, fn), 'rb').read()
    a, _ = bg8.load(d0); b, _ = bg8.load(d1); p = bg8.pal(d0); y0, y1, x0, x1 = box
    return a[y0:y1, x0:x1], b[y0:y1, x0:x1], p


def main():
    sys.stdout.reconfigure(encoding='utf-8'); os.makedirs(OUT, exist_ok=True)
    a, b, p = bgpair('TTL.BG8', (0, 224, 0, 320)); sheet('01_타이틀', '타이틀 화면(TTL.BG8) — 리본 아래 부제', [('타이틀 전체', a, b, p)], k=2)
    a, b, p = bgpair('TTL.BG8', (85, 145, 60, 250)); sheet('02_타이틀_부제확대', '타이틀 부제 확대', [('부제', a, b, p)], k=5)
    a, b, p = bgpair('DEMOLOGO.BG8', (0, 128, 0, 320)); a2, b2, _ = bgpair('DEMOLOGO.BG8', (70, 112, 90, 230))
    sheet('03_데모로고', '데모 로고(DEMOLOGO.BG8)', [('전체', a, b, p), ('부제 확대', a2, b2, p)], k=3)
    pairs = []
    for fn in ('CSEL_BG.BG8', 'CSEL_BG_.BG8'):
        a, b, p = bgpair(fn, (100, 175, 0, 320)); pairs.append((fn, a, b, p))
    sheet('04_파트너선택', '파트너 선택 이름(CSEL_BG)', pairs)
    a1, b1, p = bgpair('BATTLE0.BG8', (40, 100, 40, 280)); a2, b2, _ = bgpair('BATTLE0.BG8', (262, 322, 40, 280))
    sheet('05_배틀제목', '배틀 제목(BATTLE0.BG8) — バトル!! · バトル結果発表', [('배틀!!', a1, b1, p), ('배틀 결과 발표', a2, b2, p)])
    a, b, p = bgpair('OSIMAI.BG8', (40, 180, 0, 320)); sheet('06_끝', '끝 화면(OSIMAI.BG8) — おしまい?', [('끝?', a, b, p)], k=2)
    d0 = open(os.path.join(ARC, 'I-04.S8'), 'rb').read(); d1 = open(os.path.join(NEW, 'I-04.S8'), 'rb').read()
    sheet('07_어디로든거울', '인트로 거울(I-04.S8) — どこでもミラー', [('어디로든 거울', M.s8_load(d0), M.s8_load(d1), bg8.pal(d0))], k=2)
    p0 = cram(0); pairs = []
    for fn in ('MONNAM0.BIN', 'MONNAM1.BIN', 'MONNAM2.BIN', 'MONNAM3.BIN', 'MAONAM.BIN'):
        d0 = open(os.path.join(ARC, fn), 'rb').read(); d1 = open(os.path.join(NEW, fn), 'rb').read()
        for k in range(len(d0) // 1920):
            pairs.append(('%s #%d' % (fn, k), np.frombuffer(d0[1920 * k:1920 * (k + 1)], np.uint8).reshape(24, 80), np.frombuffer(d1[1920 * k:1920 * (k + 1)], np.uint8).reshape(24, 80), p0))
    sheet('08_적이름표_1', '적 이름표 1/2', pairs[:13], k=4); sheet('09_적이름표_2', '적 이름표 2/2', pairs[13:], k=4)
    p6 = cram(0x600); pairs = []
    d0 = open(os.path.join(ARC, 'SYSTEM.DAT'), 'rb').read(); d1 = open(os.path.join(NEW, 'SYSTEM.DAT'), 'rb').read()
    for k in range(5):
        o = 0x11C00 + 1920 * k
        pairs.append(('전투 아군 이름표 #%d' % k, np.frombuffer(d0[o:o + 1920], np.uint8).reshape(24, 80), np.frombuffer(d1[o:o + 1920], np.uint8).reshape(24, 80), p6))
    d0 = open(os.path.join(ARC, 'XCHK.BIN'), 'rb').read(); d1 = open(os.path.join(NEW, 'XCHK.BIN'), 'rb').read()
    for k in range(5):
        o = 0x3000 + 1152 * k
        pairs.append(('프로필 이름표 #%d (색은 대략)' % k, np.frombuffer(d0[o:o + 1152], np.uint8).reshape(24, 48), np.frombuffer(d1[o:o + 1152], np.uint8).reshape(24, 48), p6))
    sheet('10_아군이름표', '아군 이름표(전투 SYSTEM.DAT · 프로필 XCHK.BIN)', pairs, k=4)
    import shutil
    shutil.copyfile(os.path.join(ROOT, 'work', 'shot', 'name_preview.png'), os.path.join(OUT, '11_이름입력판.png'))
    print('→', OUT)


if __name__ == '__main__':
    main()
