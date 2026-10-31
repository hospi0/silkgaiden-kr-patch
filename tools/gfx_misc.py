# -*- coding: utf-8 -*-
r"""BG8·S8 그림 글자 한글화(2026-10-31) — 이름표 판(gfx_plates.py) 밖의 그림들
  CSEL_BG.BG8·CSEL_BG_.BG8: 파트너 선택 이름 5칸(타원 + 글자 + 흰 테두리, 타원 밖 = 0)
  python tools/gfx_misc.py → work/build/arc/*.BG8 · 미리보기 work/shot/misc_preview.png"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import bg8, gfx_plates as GP
ARC = os.path.join(ROOT, 'work', 'arc')
CSEL = [((27, 144, 69, 159), '아오'), ((83, 144, 125, 159), '아카'), ((139, 144, 181, 159), '시라후지'), ((195, 144, 237, 159), '키'), ((251, 144, 293, 159), '루리')]


def label(a, box, text):
    """타원 이름표 다시 그림: 타원 색 = 칸 안 0·흰색 빼고 최빈값, 글자 색 = 그다음, 테두리 = 흰색(가장 큰 번호 중 많은 것)"""
    x0, y0, x1, y1 = box; r = a[y0:y1, x0:x1]
    c = np.bincount(r.ravel(), minlength=256); c[0] = 0
    order = list(np.argsort(-c))
    lc = np.bincount(np.concatenate([r[:, :4].ravel(), r[:, -4:].ravel()]), minlength=256); lc[0] = 0; lc[255] = 0
    ell_c = int(np.argmax(lc))                                            # 타원 = 칸 양 끝 4열(글자 적음)
    order = [v for v in order if v != ell_c]
    fill, outline = order[0], order[1]
    if c[outline] == 0: outline = fill
    # 테두리 = 바탕(0)과 맞닿은 글자 쪽 색 — 흰색일 것
    ys, xs = np.nonzero(r == ell_c)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2; rx, ry = (xs.max() - xs.min()) / 2 + 0.5, (ys.max() - ys.min()) / 2 + 0.5
    nb = np.zeros_like(r, bool)
    z = r == 0
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)): nb |= np.roll(np.roll(z, dy, 0), dx, 1)
    oc = np.bincount(r[nb & (r != 0) & (r != ell_c)], minlength=256)
    if oc.sum(): outline = int(np.argmax(oc)); fill = [v for v in order if v not in (ell_c, outline, 0)][0]
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    ell = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
    out = np.where(ell, ell_c, 0)
    m, size = GP.fit(text, x1 - x0 - 2, y1 - y0)
    hh, ww = m.shape; oy = (y1 - y0 - hh) // 2; ox = (x1 - x0 - ww) // 2
    big = np.zeros(out.shape, bool); big[oy:oy + hh, ox:ox + ww] = m
    ol = np.zeros_like(big)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): ol |= np.roll(np.roll(big, dy, 0), dx, 1)
    out[ol & ~big] = outline; out[big] = fill
    a[y0:y1, x0:x1] = out
    return (int(ell_c), int(fill), int(outline), size)


def is_text_color(p, v):
    r, g, b = p[v]
    return not (g >= r and g >= b - 8) or r + g + b > 600 or r + g + b < 100   # 초록 판 아님 · 아주 밝음(흰 테두리) · 아주 어두움(그림자)


def inpaint(a, mask, y0, y1):
    """글자 화소를 같은 열 위·아래 가장 가까운 글자 아닌 화소로(판 무늬가 세로 결)"""
    out = a.copy()
    for x in range(a.shape[1]):
        col = mask[:, x]
        if not col.any(): continue
        good = [y for y in range(y0, y1) if not col[y]]
        for y in np.nonzero(col)[0]:
            if not good: continue
            gy = min(good, key=lambda g: abs(g - y)); out[y, x] = a[gy, x]
    return out


def title(a, p, box, text, size, skew=0.25, font=None, rowbg=None):
    """판 제목 글자: 지우고(위아래로 메움) 굵은 글꼴 + 기울임 + 원래 글자색 그라데이션(어두운→밝은 = 아래→위 반대) + 밝은 테두리"""
    x0, y0, x1, y1 = box; sub = a[y0:y1, x0:x1]
    hh0 = y1 - y0; band = sub[hh0 // 4:hh0 * 3 // 4]                        # 글자 가운데 줄들에 나오는 글자색만(금색 테두리 줄 보호)
    tv = set(v for v in np.unique(band) if is_text_color(p, v) and (band == v).sum() >= 3)
    tv |= set(v for v in np.unique(sub) if sum(p[v]) < 200 and not (p[v][1] >= p[v][0] and p[v][1] >= p[v][2]))   # 어두운 비초록(읽기 줄 테두리)
    m = np.isin(sub, list(tv))
    cols = sorted(set(sub[m].tolist()), key=lambda v: -np.bincount(sub[m])[v])[:8]
    bright = max(set(sub[m].tolist()), key=lambda v: sum(p[v]))              # 테두리 = 가장 밝은 글자색
    sat = lambda v: max(p[v]) - min(p[v])
    grad = sorted([v for v in cols if v != bright and sat(v) >= 48], key=lambda v: sum(p[v]))   # 어두움 → 밝음(무채색 빼고)
    if rowbg:                                                             # 가로 줄무늬 판: 줄마다 글자 밖(rowbg 열 범위) 최빈값 = 바탕, 다르면 글자
        bx0, bx1 = rowbg
        for y in range(y1 - y0):
            ref = a[y0 + y, bx0:bx1]; bgc = np.bincount(ref).argmax()
            m[y] = sub[y] != bgc; sub[y][m[y]] = bgc
        a[y0:y1, x0:x1] = sub
    else:
        a[y0:y1, x0:x1] = inpaint(sub, m, 0, y1 - y0)
    f = ImageFont.truetype(font or GP.FONT, size)
    im = Image.new('L', ((x1 - x0) * 2, (y1 - y0) * 2)); dr = ImageDraw.Draw(im); dr.fontmode = '1'
    dr.text((4, 4), text, font=f, fill=255)
    g = np.array(im) > 0
    ys, xs = np.nonzero(g); g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = g.shape; sh = int(skew * h)
    s = np.zeros((h, w + sh), bool)
    for y in range(h): s[y, sh - int(skew * y):sh - int(skew * y) + w] = g[y]   # 오른쪽으로 기울임
    h, w = s.shape
    if w > x1 - x0 - 2 or h > y1 - y0 - 2: raise SystemExit('⛔ 제목 칸 넘침 %s %dx%d' % (text, w, h))
    oy = y0 + (y1 - y0 - h) // 2; ox = x0 + (x1 - x0 - w) // 2
    big = np.zeros(a.shape, bool); big[oy:oy + h, ox:ox + w] = s
    ol = np.zeros_like(big)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): ol |= np.roll(np.roll(big, dy, 0), dx, 1)
    a[ol & ~big] = bright
    for y in range(oy, oy + h):
        k = int((y - oy) / max(1, h - 1) * (len(grad) - 1)); v = grad[::-1][k] if grad else bright
        a[y][big[y]] = v                                                  # 위 = 밝음, 아래 = 어두움
    return (bright, grad)


def erase_rows(a, box, rowbg):
    """글자 없이 지우기만(가로 줄무늬 판) — 줄마다 rowbg 열 최빈값으로"""
    x0, y0, x1, y1 = box; bx0, bx1 = rowbg
    for y in range(y0, y1):
        bgc = np.bincount(a[y, bx0:bx1]).argmax(); a[y, x0:x1] = bgc


PEN = os.path.join('C:' + os.sep, 'claude', 'utils', 'font', 'nanum-pen', 'NanumPenScript-Regular.ttf')
JUA = os.path.join('C:' + os.sep, 'claude', 'utils', 'font', 'jua', 'Jua-Regular.ttf')


def cover(text, font, size, ss=4):
    f = ImageFont.truetype(font, size * ss); w = int(size * ss * (len(text) + 1)); h = int(size * ss * 2)
    im = Image.new('L', (w, h)); ImageDraw.Draw(im).text((ss * 4, ss * 4), text, font=f, fill=255)
    a = np.asarray(im.resize((w // ss, h // ss), Image.BOX), dtype=float) / 255
    ys, xs = np.nonzero(a > 0.05); return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def osimai(a):
    """OSIMAI.BG8 「おしまい?」 → 「끝?」: 검은 바탕 5 · 글자 흰 1 + 회색 단계 2·3·4(안티)"""
    a[80:140, 60:270] = 5
    g = cover('끝?', PEN, 110); h, w = g.shape
    oy = 108 - h // 2; ox = 168 - w // 2
    lv = np.select([g > 0.85, g > 0.6, g > 0.35, g > 0.12], [1, 2, 3, 4], 5)
    reg = a[oy:oy + h, ox:ox + w]; a[oy:oy + h, ox:ox + w] = np.where(lv != 5, lv, reg)


def s8_load(d):
    import struct
    x, y, w, h = struct.unpack_from('>4H', d, 0x200)
    return np.frombuffer(d[0x208:0x208 + w * h], np.uint8).reshape(h, w).astype(int)


def peel(a, mask):
    """양파 껍질 메우기: 지울 화소를 바깥부터 한 겹씩, 이미 아는 4이웃 색의 최빈값으로"""
    a = a.copy(); m = mask.copy(); H, W = a.shape
    while m.any():
        known = ~m; nxt = []
        for y, x in zip(*np.nonzero(m)):
            vs = [a[yy, xx] for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)) if 0 <= yy < H and 0 <= xx < W and known[yy, xx]]
            if vs: nxt.append((y, x, max(set(vs), key=vs.count)))
        if not nxt: break
        for y, x, v in nxt: a[y, x] = v; m[y, x] = False
    return a


def mirror(d):
    """I-04.S8 「どこでもミラー」 → 「어디로든 거울」: 흰 글자 + 검은 테두리 — 지우고 위아래로 메움, 주아 글꼴"""
    p = bg8.pal(d); a = s8_load(d); h0, w0 = a.shape
    y0, y1 = 108, 154
    sub = a[y0:y1]
    def txt(v):
        r, g, b = p[v]; return (min(r, g, b) >= 200 and max(r, g, b) - min(r, g, b) <= 40) or r + g + b < 60
    blk = np.vectorize(lambda v: sum(p[v]) < 300 and max(p[v]) - min(p[v]) < 80)(sub)   # 테두리 = 어둡고 채도 낮음(짙은 빨강 폭발 빼고)
    wht = np.vectorize(lambda v: min(p[v]) >= 190 and max(p[v]) - min(p[v]) <= 50)(sub)
    near = blk.copy()
    for _ in range(4):
        n2 = near.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)): n2 |= np.roll(np.roll(near, dy, 0), dx, 1)
        near = n2
    m = blk | (wht & near)                                                # 글자 = 검은 테두리 + 그 근처 흰 화소(폭발의 흰 빛 제외)
    mm = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): mm |= np.roll(np.roll(m, dy, 0), dx, 1)
    a[y0:y1] = peel(sub, mm)
    white = min((v for v in range(256) if min(p[v]) >= 230), key=lambda v: -sum(p[v]))
    black = min(range(256), key=lambda v: sum(p[v]))
    g = cover('어디로든 거울', JUA, 30) > 0.5; h, w = g.shape
    oy = (y0 + y1) // 2 - h // 2; ox = w0 // 2 - w // 2
    big = np.zeros(a.shape, bool); big[oy:oy + h, ox:ox + w] = g
    ol = np.zeros_like(big)
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            if abs(dy) + abs(dx) <= 3: ol |= np.roll(np.roll(big, dy, 0), dx, 1)
    a[ol & ~big] = black; a[big] = white
    return d[:0x208] + bytes(a.astype(np.uint8).ravel()) + d[0x208 + h0 * w0:], a, s8_load(d), p


def label8(m):
    """8방향 연결 덩어리 번호(scipy 없이)"""
    lab = np.zeros(m.shape, int); n = 0; H, W = m.shape
    for y0, x0 in zip(*np.nonzero(m)):
        if lab[y0, x0]: continue
        n += 1; st = [(y0, x0)]; lab[y0, x0] = n
        while st:
            y, x = st.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not lab[yy, xx]: lab[yy, xx] = n; st.append((yy, xx))
    return lab, n


GAL9 = os.path.join('C:' + os.sep, 'claude', 'utils', 'font', 'Galmuri-v2.40.3', 'Galmuri9.ttf')


def ttl_logo(a, p, text='스고벤처'):
    """TTL.BG8 큰 로고 「すごべんちゃー」: 노란 글자·어두운 테두리·그림자 싹 지우고(띠·모래로 메움)
       한글을 파란 띠 윗선(곡선)을 따라 글자마다 접선 각도로 돌려 놓음(하스피 2026-10-31)"""
    y0, y1, x0, x1 = 0, 126, 20, 282
    reg = a[y0:y1, x0:x1]
    yel = np.vectorize(lambda v: p[v][0] >= 200 and p[v][2] <= 40)(reg)
    dark = np.vectorize(lambda v: sum(p[v]) < 420 and not p[v][2] > p[v][0])(reg)
    blue = np.vectorize(lambda v: p[v][2] > p[v][0])(reg)
    near = yel.copy()
    for _ in range(4):
        n2 = near.copy()
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1)): n2 |= np.roll(np.roll(near, dy, 0), dx, 1)
        near = n2
    mask = yel | (dark & near)
    mask[:, 236:] &= ~np.vectorize(lambda v: max(p[v]) - min(p[v]) < 40)(reg)[:, 236:]   # TM·주사위(무채색) 보호
    fill = int(np.bincount(reg[yel]).argmax())
    oc = np.bincount(reg[dark & near & ~yel], minlength=256); outline = int(oc.argmax())
    # 띠 윗선: 열마다 첫 파랑 줄(글자 지우기 전 — 글자에 가린 열은 빼고 곡선 맞춤)
    xs, ys = [], []
    for x in range(reg.shape[1]):
        col = np.nonzero(blue[:, x])[0]
        if len(col) and not mask[max(0, col[0] - 2):col[0] + 1, x].any(): xs.append(x); ys.append(col[0])
    coef = np.polyfit(xs, ys, 2)
    a[y0:y1, x0:x1] = peel(reg, mask)
    L, R = 8, 232                                                         # 원래 로고 가로 범위(す ~ ー)
    n = len(text); step = (R - L) / n
    f = ImageFont.truetype(JUA, 56)
    for i, ch in enumerate(text):
        cx = L + step * (i + 0.5); cy = np.polyval(coef, cx) - 2
        ang = np.degrees(np.arctan(2 * coef[0] * cx + coef[1]))
        im = Image.new('L', (90, 90)); dr = ImageDraw.Draw(im); dr.fontmode = '1'
        dr.text((45, 45), ch, font=f, fill=255, anchor='mm')
        im = im.rotate(-ang, resample=Image.NEAREST, center=(45, 45))
        g = np.array(im) > 0
        gy, gx = int(round(y0 + cy)) - 45, int(round(x0 + cx)) - 45
        H, W = a.shape; yy0, xx0 = max(0, gy), max(0, gx)
        sub = a[yy0:gy + 90, xx0:gx + 90]; g = g[yy0 - gy:yy0 - gy + sub.shape[0], xx0 - gx:xx0 - gx + sub.shape[1]]
        ol = np.zeros_like(g)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if abs(dy) + abs(dx) <= 3: ol |= np.roll(np.roll(g, dy, 0), dx, 1)
        sh = np.zeros_like(g)
        for k in (2, 3, 4): sh |= np.roll(np.roll(ol, k, 0), k, 1)
        sub[sh & ~ol] = outline; sub[ol & ~g] = outline; sub[g] = fill
    return (fill, outline, [round(c, 4) for c in coef])


def ttl_sub(a, p, text='·드래곤 마스터 실크 외전·', erase_only=False):
    """TTL.BG8 리본 아래 휜 부제 「・ドラゴンマスターシルク外伝・」 → 한글(하스피 2026-10-31: 일본어 싹 지우고 배경부터 깔끔히, 글자는 호 각도대로)
       1) 리본 아래 끝 곡선 = 열마다 아래(y136)에서 위로 처음 만나는 리본 파랑(파랑≥140·빨강·초록<60 — 부제 남색과 구분) → 2차 곡선(이상치 빼고)
       2) 곡선 아래 3줄 = 리본 그림자색, 그 아래 ~ y140 = 같은 열 40px 아래 깨끗한 모래 그대로(x 70~232, 주사위 밖)
       3) 한글: 곡선 아래 그림자 다음 줄에 글자 중심, 접선 각도로 돌림(4배로 그려 돌려 줄임), 그림자→테두리→채움 한꺼번에"""
    RB = np.vectorize(lambda v: p[v][2] >= 140 and p[v][0] < 60 and p[v][1] < 60)(a)
    xs, ys = [], []
    for x in range(70, 233):
        y = 136
        while y > 80 and not RB[y, x]: y -= 1
        if y > 80: xs.append(x); ys.append(y + 1)
    xs = np.array(xs); ys = np.array(ys)
    for _ in range(4):
        coef = np.polyfit(xs, ys, 2); keep = np.abs(ys - np.polyval(coef, xs)) < 2; xs, ys = xs[keep], ys[keep]
    orig = a.copy()
    shc = [v for v in range(256) if p[v] == (120, 96, 56)]                 # 리본 그림자색(원본 66·67·68)
    for x in range(82, 231):
        e = int(round(np.polyval(coef, x)))
        rib_above = RB[e - 1, x] or RB[e - 2, x]
        for y in range(e, 141):
            if RB[y, x]: continue
            if y < e + 3 and rib_above: a[y, x] = orig[y, x] if orig[y, x] in shc else shc[(x + y) % len(shc)]
            elif y >= e + 3 or not rib_above: a[y, x] = orig[y + 40, x]
    if erase_only: return coef
    light = min(range(256), key=lambda v: sum((np.array(p[v]) - (240, 248, 248)) ** 2))
    dark = min(range(256), key=lambda v: sum((np.array(p[v]) - (0, 0, 88)) ** 2))
    shadow = shc[0]
    SS = 4; size = 11
    f = ImageFont.truetype(GP.FONT, size * SS)                            # ExtraBold — 돌려도 획이 버팀
    L, R = 84, 220
    widths = [max(4, f.getlength(c) / SS) for c in text]; total = sum(widths); scale = (R - L) / total
    G = np.zeros(a.shape, bool); xcur = L
    for c, w in zip(text, widths):
        cx = xcur + w * scale / 2; xcur += w * scale
        if c == ' ': continue
        cy = np.polyval(coef, cx) + 9; ang = np.degrees(np.arctan(2 * coef[0] * cx + coef[1]))
        im = Image.new('L', (20 * SS, 20 * SS)); dr = ImageDraw.Draw(im)
        dr.text((10 * SS, 10 * SS), c, font=f, fill=255, anchor='mm')
        im = im.rotate(-ang, resample=Image.BICUBIC, center=(10 * SS, 10 * SS))
        g = np.asarray(im.resize((20, 20), Image.BOX), dtype=float) / 255 > 0.45
        gy, gx = int(round(cy)) - 10, int(round(cx)) - 10
        G[gy:gy + 20, gx:gx + 20] |= g
    O = np.zeros_like(G)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): O |= np.roll(np.roll(G, dy, 0), dx, 1)
    S = np.roll(np.roll(O, 1, 0), 1, 1)
    a[S & ~O] = shadow; a[O & ~G] = dark; a[G] = light
    return (light, dark, shadow, [round(c, 4) for c in coef])


def demo_sub(a, p, text='·드래곤 마스터 실크 외전·', erase_only=False):
    """DEMOLOGO.BG8 작은 로고 리본 아래 부제 → 한글(타이틀과 같은 방식)
       리본 아래 경계 = 밝은 파랑 1px + 그 위 중간 파랑 1px + 안 남색 — 부제 없는 양쪽 열(x 95~115·205~221)에서 아래→위 첫 비검정으로 2차 곡선
       x 112~208 다시 칠함: 곡선 위 = 노랑·리본 파랑 아닌 화소만 남색 / 곡선 −1 = 중간 파랑 / 곡선 = 경계 파랑 / 아래 = 검정(0)"""
    near = lambda rgb: min(range(256), key=lambda v: sum((np.array(p[v]) - rgb) ** 2))
    inner, mid, border = near((0, 0, 128)), near((0, 0, 160)), near((40, 48, 192))
    xs, ys = [], []
    for x in list(range(95, 116)) + list(range(205, 222)):
        y = 112
        while y > 60 and a[y, x] == 0: y -= 1
        xs.append(x); ys.append(y)
    coef = np.polyfit(xs, ys, 2)
    yel = lambda v: p[v][0] >= 200 and p[v][2] <= 40
    rib = lambda v: p[v][2] >= 120 and p[v][0] <= 48 and p[v][1] <= 56
    lt = np.array([[sum(p[v]) > 450 and not yel(v) for v in row] for row in a[84:107, 112:210]])   # 원래 부제 글자(흰·회색) 중심선
    cx_, cy_ = [], []
    for x in range(lt.shape[1]):
        ys_ = np.nonzero(lt[:, x])[0]
        if len(ys_): cx_.append(112 + x); cy_.append(84 + ys_.mean())
    tcoef = np.polyfit(cx_, cy_, 2)
    logo = lambda v: yel(v) or (p[v][0] >= 80 and p[v][0] > p[v][1] > p[v][2])      # 로고 글자 노랑·갈색 테두리 — 리본 경계 아래로도 삐져나옴
    for x in range(112, 209):
        e = int(round(np.polyval(coef, x)))
        for y in range(80, 108):
            if logo(a[y, x]): continue
            if y < e - 1:
                if not yel(a[y, x]) and not rib(a[y, x]): a[y, x] = inner
            elif y == e - 1: a[y, x] = mid
            elif y == e: a[y, x] = border
            else: a[y, x] = 0
    if erase_only: return coef
    light = near((240, 248, 248)); dark = near((0, 0, 88))
    SS = 4; size = 9
    f = ImageFont.truetype(GP.FONT, size * SS)
    L, R = 108, 212
    widths = [max(3, f.getlength(c) / SS) for c in text]; total = sum(widths); scale = (R - L) / total
    G = np.zeros(a.shape, bool); xcur = L
    for c, w in zip(text, widths):
        cx = xcur + w * scale / 2; xcur += w * scale
        if c == ' ': continue
        cy = np.polyval(tcoef, cx); ang = np.degrees(np.arctan(2 * tcoef[0] * cx + tcoef[1]))
        im = Image.new('L', (16 * SS, 16 * SS)); dr = ImageDraw.Draw(im)
        dr.text((8 * SS, 8 * SS), c, font=f, fill=255, anchor='mm')
        im = im.rotate(-ang, resample=Image.BICUBIC, center=(8 * SS, 8 * SS))
        g = np.asarray(im.resize((16, 16), Image.BOX), dtype=float) / 255 > 0.45
        gy, gx = int(round(cy)) - 8, int(round(cx)) - 8
        G[gy:gy + 16, gx:gx + 16] |= g
    O = np.zeros_like(G)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): O |= np.roll(np.roll(G, dy, 0), dx, 1)
    a[O & ~G] = dark; a[G] = light
    return (light, dark, [round(c, 4) for c in tcoef])


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    od = os.path.join(ROOT, 'work', 'gfx_out'); os.makedirs(od, exist_ok=True)
    shots = []
    for fn in ('CSEL_BG.BG8', 'CSEL_BG_.BG8'):
        d = open(os.path.join(ARC, fn), 'rb').read(); a, info = bg8.load(d); b = a.copy()
        for box, t in CSEL: print(fn, t, label(b, box, t))
        out, ch, add = bg8.save(d, b); open(os.path.join(od, fn), 'wb').write(out)
        print(fn, '바뀐 칸', ch, '새 타일', add, len(d), '→', len(out))
        p = bg8.pal(d); shots.append((fn, a[130:170], b[130:170], p))
    fn = 'BATTLE0.BG8'; d = open(os.path.join(ARC, fn), 'rb').read(); a, info = bg8.load(d); b = a.copy(); p = bg8.pal(d)
    print(fn, '배틀!!', title(b, p, (92, 50, 238, 94), '배틀!!', 34))
    print(fn, '배틀 결과 발표', title(b, p, (84, 272, 231, 316), '배틀 결과 발표', 21, skew=0.2, rowbg=(60, 80)))
    erase_rows(b, (231, 284, 240, 316), (60, 80))                         # 칸 밖에 남은 「表」 꼬리(빗금 없는 아래 줄)
    out, ch, add = bg8.save(d, b); open(os.path.join(od, fn), 'wb').write(out); print(fn, '바뀐 칸', ch, '새 타일', add, len(d), '→', len(out))
    shots.append((fn, a[40:100, :320], b[40:100, :320], p)); shots.append((fn, a[262:322, :320], b[262:322, :320], p))
    fn = 'OSIMAI.BG8'; d = open(os.path.join(ARC, fn), 'rb').read(); a, info = bg8.load(d); b = a.copy(); osimai(b)
    out, ch, add = bg8.save(d, b); open(os.path.join(od, fn), 'wb').write(out); print(fn, '바뀐 칸', ch, '새 타일', add, len(d), '→', len(out))
    shots.append((fn, a[60:160], b[60:160], bg8.pal(d)))
    fn = 'I-04.S8'; d = open(os.path.join(ARC, fn), 'rb').read(); out, b, a, p = mirror(d); open(os.path.join(od, fn), 'wb').write(out)
    print(fn, len(d), '→', len(out)); shots.append((fn, a, b, p))
    fn = 'DEMOLOGO.BG8'; d = open(os.path.join(ARC, fn), 'rb').read(); a, info = bg8.load(d); b = a.copy(); p = bg8.pal(d)
    print(fn, demo_sub(b, p)); out, ch, add = bg8.save(d, b); open(os.path.join(od, fn), 'wb').write(out)
    print(fn, '바뀐 칸', ch, '새 타일', add, len(d), '→', len(out)); shots.append((fn, a, b, p))
    for fn in ('TTL.BG8',):
        d = open(os.path.join(ARC, fn), 'rb').read(); a, info = bg8.load(d); b = a.copy(); p = bg8.pal(d)
        print(fn, ttl_sub(b, p)); out, ch, add = bg8.save(d, b); open(os.path.join(od, fn), 'wb').write(out)
        print(fn, '바뀐 칸', ch, '새 타일', add, len(d), '→', len(out)); shots.append((fn, a[0:150], b[0:150], p))
    S = Image.new('RGB', (320 * 3, sum(2 * s[1].shape[0] * 3 for s in shots)), (30, 30, 30)); y = 0
    for fn, a, b, p in shots:
        for z in (a, b):
            im = Image.fromarray(np.array([[p[v] for v in r] for r in z], dtype=np.uint8)); im = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
            S.paste(im, (0, y)); y += im.height
    S.save(os.path.join(ROOT, 'work', 'shot', 'misc_preview.png'))


if __name__ == '__main__':
    main()
