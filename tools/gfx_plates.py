# -*- coding: utf-8 -*-
r"""이름표 그림 한글화(2026-10-31) — 8비트 색번호 그림(80×24 적 이름표·48×24 프로필 이름·80×24 전투 아군 이름표)
  판마다: 글자 칸(LEFT..RIGHT·TOP..BOTTOM) 안에서 «바탕 색번호»(칸 테두리 줄에서 가장 많은 값) 아닌 화소 = 원래 글자 → 바탕으로 지움
          글자 색 = 지운 화소 중 가장 많은 값 · 테두리 색 = 바탕과 맞닿은 지운 화소 중 가장 많은 값
          한글 = 나눔고딕 ExtraBold 모노(가장 큰 크기로 칸 안에) + 테두리 1px(8방향)
  python tools/gfx_plates.py → work/build/arc/MONNAM0~3.BIN·MAONAM.BIN · 미리보기 work/shot/plates_preview.png(전투 스테이트 30 팔레트)"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(ROOT, 'work', 'arc')
FONT = os.path.join('C:' + os.sep, 'claude', 'utils', 'font', 'nanum-gothic', 'NanumGothicExtraBold.ttf')
MON = {   # 파일 → 6장 이름(원문은 docs/00_초기조사.md)
    'MONNAM0.BIN': ['가고일', '어둠 엘프', '본데드', '암석 마인', '하이 골렘', '라디'],
    'MONNAM1.BIN': ['리틀 비', '어비스 레이디', '서큐버스Ⅱ', '보석 마인', '미스트 레이디', '아만다'],
    'MONNAM2.BIN': ['스켈레톤', '이클립스', '데스 골렘', '사탄 나이트', '와이번α', '마왕'],
    'MONNAM3.BIN': ['가디언', '사이클롭스', '데비어스', '와이번β', '와이번β', '루네'],
    'MAONAM.BIN': ['마왕'],
}
W, H = 80, 24
GRAD = {('MAONAM.BIN', 0): (50, 16), ('MONNAM2.BIN', 5): (50, 16), ('MONNAM3.BIN', 5): (50, 16)}   # 노란 그라데이션 글자 → 글자 50·테두리 16
BOX = (4, 3, 76, 21)                      # 글자 칸(x0, y0, x1, y1) — 판 테두리 안


def mask_text(ch_list, size, maxw, maxh):
    text = ch_list
    f = ImageFont.truetype(FONT, size)
    im = Image.new('1', (maxw * 3, maxh * 3)); d = ImageDraw.Draw(im); d.fontmode = '1'
    d.text((2, 2), text, font=f, fill=1)
    a = np.array(im, dtype=bool)
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(xs) else a[:1, :1]


def fit(text, maxw, maxh):
    for size in range(24, 7, -1):
        m = mask_text(text, size, maxw, maxh)
        if m.shape[1] + 2 <= maxw and m.shape[0] + 2 <= maxh: return m, size
    raise SystemExit('⛔ 칸에 안 들어감 %s' % text)


def redo(img, text, box=BOX, colors=None, band=(24, 56), bgx=(12, 68), bgy=(2, 21), bgarea=None):
    a = img.copy(); x0, y0, x1, y1 = box
    region = a[y0:y1, x0:x1]
    bg = np.bincount(np.concatenate([a[bgy[0], bgx[0]:bgx[1]], a[bgy[1], bgx[0]:bgx[1]]])).argmax()
    if bgarea:                                                            # 바탕을 글자 옆 빈 칸에서(위아래 줄에 글자 테두리가 섞이는 판)
        ax0, ay0, ax1, ay1 = bgarea; bg = np.bincount(a[ay0:ay1, ax0:ax1].ravel()).argmax()   # 판 바탕 = 글자 줄 바로 위·아래 줄(장식 빼고) 최빈값
    band = region[1:-1, band[0] - x0:band[1] - x0]
    cnt = np.bincount(band.ravel(), minlength=256); cnt[bg] = 0
    tv = [v for v in range(256) if cnt[v] >= 3]                          # 글자 색들(가운데 띠에 나오는 색) — 양 끝 장식은 다른 색
    tvm = np.isin(region, tv)
    cols = np.nonzero(tvm.sum(axis=0) >= 2)[0]
    runs = []; s = cols[0]; p = cols[0]
    for c in cols[1:]:
        if c - p > 3: runs.append((s, p)); s = c
        p = c
    runs.append((s, p)); cx0, cx1 = max(runs, key=lambda r: r[1] - r[0])
    tm = np.zeros_like(tvm); tm[:, cx0:cx1 + 1] = tvm[:, cx0:cx1 + 1]
    nb = np.zeros_like(tm)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nb |= np.roll(np.roll(~tm, dy, 0), dx, 1)
    inner = region[tm & ~nb]; ov = region[tm & nb]
    fill = np.bincount(inner).argmax() if len(inner) else 15             # 글자 색 = 바탕과 안 닿은 안쪽
    c = np.bincount(ov, minlength=256); c[fill] = 0; outline = c.argmax() if c.sum() else bg
    if colors: fill, outline = colors                                     # 그라데이션 글자 판(마왕·루네)
    region[tm] = bg
    sub = region[:, cx0:cx1 + 1]; nz = sub != bg                          # 글자 범위 안 외톨이 화소(원본 잔재) 지움
    nbc = sum(np.roll(np.roll(nz, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) - nz
    sub[nz & (nbc <= 1)] = bg
    m, size = fit(text, cx1 - cx0 + 1 + 6 if cx1 - cx0 + 7 <= x1 - x0 else x1 - x0, y1 - y0)
    hh, ww = m.shape
    oy = (y1 - y0 - hh) // 2; ox = (cx0 + cx1) // 2 - ww // 2
    ox = max(1, min(ox, x1 - x0 - ww - 2))
    big = np.zeros((y1 - y0, x1 - x0), bool); big[oy:oy + hh, ox:ox + ww] = m
    ol = np.zeros_like(big)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ol |= np.roll(np.roll(big, dy, 0), dx, 1)
    ol |= np.roll(np.roll(big, 2, 0), 2, 1) | np.roll(np.roll(big, 2, 0), 1, 1) | np.roll(np.roll(big, 1, 0), 2, 1)   # 오른쪽 아래 그림자
    region[ol & ~big] = outline
    if colors:                                                            # 그라데이션: 글자 가운데 줄 14 → 위아래로 10
        ys = np.nonzero(big.any(axis=1))[0]; cy = (ys.min() + ys.max()) / 2; half = max(1, (ys.max() - ys.min()) / 2)
        for y in ys: region[y][big[y]] = int(round(14 - 4 * abs(y - cy) / half))
    else:
        region[big] = fill
    return a, (bg, fill, outline, size)


def profile(a, text):
    """프로필 이름표 48×24: 타원(바탕색 1개) 위 큰 글자(글자색+테두리)가 타원 밖으로 삐져나옴
       → 바탕색 화소 범위로 타원을 다시 그리고(밖은 0 투명) 그 위에 글자"""
    vals = np.bincount(a.ravel(), minlength=256); vals[0] = 0
    bg = int(np.argmax(vals))                                              # 가장 많은 색 = 타원
    ys, xs = np.nonzero(a == bg)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2; rx, ry = (xs.max() - xs.min()) / 2 + 0.5, (ys.max() - ys.min()) / 2 + 0.5
    other = a[(a != 0) & (a != bg)]
    c = np.bincount(other, minlength=256)
    fill = int(np.argmax(c)); c[fill] = 0; outline = int(np.argmax(c)) if c.sum() else bg
    yy, xx = np.mgrid[0:24, 0:48]
    ell = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
    b = np.where(ell, bg, 0)
    m, size = fit(text, 46, 22)
    hh, ww = m.shape; oy = (24 - hh) // 2; ox = (48 - ww) // 2
    big = np.zeros((24, 48), bool); big[oy:oy + hh, ox:ox + ww] = m
    ol = np.zeros_like(big)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): ol |= np.roll(np.roll(big, dy, 0), dx, 1)
    b[ol & ~big] = outline; b[big] = fill
    return b, (bg, fill, outline, size)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    c = open(os.path.join(ROOT, 'work', 'mem', 's30', 'CRAM.bin'), 'rb').read()
    pal = [((w & 31) * 8, ((w >> 5) & 31) * 8, ((w >> 10) & 31) * 8) for w in (struct.unpack_from('<H', c, 2 * k)[0] for k in range(256))]
    od = os.path.join(ROOT, 'work', 'gfx_out'); os.makedirs(od, exist_ok=True)
    rows = []
    for fn, names in MON.items():
        d = bytearray(open(os.path.join(ARC, fn), 'rb').read())
        for k, t in enumerate(names):
            a = np.frombuffer(bytes(d[W * H * k:W * H * (k + 1)]), np.uint8).reshape(H, W).astype(int)
            b, info = redo(a, t, colors=GRAD.get((fn, k)))
            d[W * H * k:W * H * (k + 1)] = bytes(b.astype(np.uint8).ravel())
            rows.append((fn, k, t, a, b, info))
        open(os.path.join(od, fn), 'wb').write(bytes(d))
    # 아군 이름표: SYSTEM.DAT 전투용 80×24(오른쪽 원형 장식 → 글자 칸 x 3~64) · XCHK.BIN 0x3000 프로필용 48×24(앞 5장 = 일본어, 뒤 5장 로마자 그대로)
    PN = ['아오', '아카', '키', '루리', '시라후지']
    sd = bytearray(open(os.path.join(ARC, 'SYSTEM.DAT'), 'rb').read())
    for k, t in enumerate(PN):
        o = 0x11C00 + 1920 * k
        a = np.frombuffer(bytes(sd[o:o + 1920]), np.uint8).reshape(24, 80).astype(int)
        b, info = redo(a, t, box=(3, 1, 64, 23), band=(14, 50), bgx=(6, 60), bgy=(2, 21), bgarea=(8, 6, 17, 19))
        sd[o:o + 1920] = bytes(b.astype(np.uint8).ravel()); rows.append(('SYSTEM.DAT', k, t, a, b, info))
    open(os.path.join(od, 'SYSTEM.DAT'), 'wb').write(bytes(sd))
    xc = bytearray(open(os.path.join(ARC, 'XCHK.BIN'), 'rb').read())
    for k, t in enumerate(['아오', '아카', '시라후지', '키', '루리']):        # XCHK 판 차례(그림으로 확인)
        o = 0x3000 + 1152 * k
        a = np.frombuffer(bytes(xc[o:o + 1152]), np.uint8).reshape(24, 48).astype(int)
        b, info = profile(a, t)
        b2 = np.full((24, 80), b[0, 0]); b2[:, :48] = b; a2 = np.full((24, 80), a[0, 0]); a2[:, :48] = a
        xc[o:o + 1152] = bytes(b.astype(np.uint8).ravel()); rows.append(('XCHK.BIN', k, t, a2, b2, info))
    open(os.path.join(od, 'XCHK.BIN'), 'wb').write(bytes(xc))
    pal6 = [((w & 31) * 8, ((w >> 5) & 31) * 8, ((w >> 10) & 31) * 8) for w in (struct.unpack_from('<H', c, 2 * (0x600 + k))[0] for k in range(256))]
    S = Image.new('RGB', (2 * (W + 8) * 3, len(rows) * (H + 4) * 3), (30, 30, 30))
    for i, (fn, k, t, a, b, info) in enumerate(rows):
        for j, z in enumerate((a, b)):
            pp = pal6 if fn in ('SYSTEM.DAT', 'XCHK.BIN') else pal
            im = Image.fromarray(np.array([[pp[v] for v in r] for r in z], dtype=np.uint8)).resize((W * 3, H * 3), Image.NEAREST)
            S.paste(im, (j * (W + 8) * 3, i * (H + 4) * 3))
    S.save(os.path.join(ROOT, 'work', 'shot', 'plates_preview.png'))
    for fn, k, t, a, b, info in rows: print(fn, k, t, '바탕·글자·테두리·크기', info)


if __name__ == '__main__':
    main()
