# -*- coding: utf-8 -*-
r"""SPAN 스프라이트 묶음(2026-10-31) — 'SPAN' · u32 크기 · u16 팔레트 수 · u16 스프라이트 수 · u16 ? · u16 0
  0x10 팔레트 (수×16색, RGB555 BE) → 표 16 B × 스프라이트 수: u32 위치 · u16 ? · u16 ? · u16 크기 · u16 0 · u8 정렬 폭 · u8 높이 · u16 0
  화소 4비트(폭×높이/2) — 팔레트 번호는 표에 없음(게임이 정함) → 미리보기는 팔레트 0
  python tools/span.py 파일… → work/gfx/span_<파일>.png(번호 붙인 모음)"""
import os, struct, sys
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse(d):
    assert d[:4] == b'SPAN'
    npal, nspr = struct.unpack_from('>HH', d, 8)
    pals = [[((v & 31) * 8, (v >> 5 & 31) * 8, (v >> 10 & 31) * 8) for v in struct.unpack_from('>16H', d, 0x10 + 32 * p)] for p in range(npal)]
    t = 0x10 + 32 * npal; spr = []
    for k in range(nspr):
        off, a, b, size, _, bw, bh, _2 = struct.unpack_from('>IHHHHBBH', d, t + 16 * k)
        spr.append((off, bw, bh, size, a, b))
    return pals, spr


def image(d, s, pal):
    off, bw, bh, size = s[:4]
    im = Image.new('RGB', (bw, bh))
    px = []
    for i in range(bw * bh):
        b = d[off + i // 2] if off + i // 2 < len(d) else 0
        px.append(pal[(b >> 4) if i % 2 == 0 else b & 15])
    im.putdata(px); return im


def main():
    for f in sys.argv[1:]:
        d = open(os.path.join(ROOT, 'work', 'arc', f), 'rb').read(); pals, spr = parse(d)
        W = 1200; x = y = rh = 0; ims = []
        for k, s in enumerate(spr):
            im = image(d, s, pals[0]).resize((s[1] * 2, s[2] * 2), Image.NEAREST)
            if x + im.width > W: x = 0; y += rh + 12; rh = 0
            ims.append((x, y, k, im)); x += im.width + 4; rh = max(rh, im.height)
        S = Image.new('RGB', (W, y + rh + 14), (40, 40, 40)); dr = ImageDraw.Draw(S)
        for x, y, k, im in ims: S.paste(im, (x, y + 10)); dr.text((x, y), str(k), fill=(255, 255, 0))
        S.save(os.path.join(ROOT, 'work', 'gfx', 'span_%s.png' % f)); print(f, len(pals), '팔레트', len(spr), '조각', S.size)


if __name__ == '__main__':
    main()
