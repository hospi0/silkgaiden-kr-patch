# -*- coding: utf-8 -*-
r"""S8·BG8 그림 펼치기(2026-10-31) — 앞 512 B = 팔레트 256색(RGB555 BE, 0x8000 비트 = 불투명 표시?)
  S8: 0x200 u16 x·y·폭·높이 + 8비트 화소(폭×높이) — 크기가 넘치면 같은 꼴 프레임이 이어짐(머리 8 B 마다)
  BG8: 0x200 u16 칸 폭·칸 높이·타일 수·? + u16 맵(칸 폭×칸 높이) + 타일 8×8 8비트
  python tools/gfx_dump.py → work/gfx/<이름>.png + 모음 work/shot/gfx_sheet_*.png"""
import os, struct, sys
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(ROOT, 'work', 'arc')


def pal(d):
    return [((v & 31) * 8, (v >> 5 & 31) * 8, (v >> 10 & 31) * 8) for v in struct.unpack_from('>256H', d, 0)]


def s8(d):
    p = pal(d); o = 0x200; out = []
    while o + 8 <= len(d):
        x, y, w, h = struct.unpack_from('>4H', d, o); o += 8
        if not (0 < w <= 704 and 0 < h <= 512) or o + w * h > len(d): break
        im = Image.new('RGB', (w, h)); im.putdata([p[b] for b in d[o:o + w * h]]); out.append(im); o += w * h
    return out


def bg8(d):
    p = pal(d); cw, ch, nt, _ = struct.unpack_from('>4H', d, 0x200)
    mo = 0x208; to = mo + 2 * cw * ch
    im = Image.new('RGB', (cw * 8, ch * 8))
    for k in range(cw * ch):
        t = struct.unpack_from('>H', d, mo + 2 * k)[0]; tile = d[to + 64 * t:to + 64 * t + 64]
        if len(tile) < 64: continue
        ti = Image.new('RGB', (8, 8)); ti.putdata([p[b] for b in tile]); im.paste(ti, ((k % cw) * 8, (k // cw) * 8))
    return [im]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    od = os.path.join(ROOT, 'work', 'gfx'); os.makedirs(od, exist_ok=True)
    items = []
    for f in sorted(os.listdir(ARC)):
        if not f.endswith(('.S8', '.BG8')): continue
        d = open(os.path.join(ARC, f), 'rb').read()
        try: ims = s8(d) if f.endswith('.S8') else bg8(d)
        except Exception as e: print('실패', f, e); continue
        if not ims: print('프레임 없음', f); continue
        for i, im in enumerate(ims[:4]):
            nm = f + ('' if i == 0 else '_%d' % i); im.save(os.path.join(od, nm + '.png')); items.append((nm, im, len(ims)))
    page = []; pages = []; x = y = rh = 0
    for nm, im, n in items:
        t = im.copy(); t.thumbnail((200, 160))
        if x + t.width > 1200: x = 0; y += rh + 14; rh = 0
        if y + t.height + 14 > 1000: pages.append(page); page = []; x = y = rh = 0
        page.append((x, y, nm, t, n)); x += t.width + 6; rh = max(rh, t.height)
    pages.append(page)
    for k, pg in enumerate(pages):
        S = Image.new('RGB', (1200, 1000), (40, 40, 40)); dr = ImageDraw.Draw(S)
        for x, y, nm, t, n in pg: S.paste(t, (x, y + 12)); dr.text((x, y), nm + ('(%d)' % n if n > 1 else ''), fill=(255, 255, 0))
        S.save(os.path.join(ROOT, 'work', 'shot', 'gfx_sheet_%d.png' % k))
    print(len(items), '장 ·', len(pages), '쪽')


if __name__ == '__main__':
    main()
