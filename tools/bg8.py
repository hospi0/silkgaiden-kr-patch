# -*- coding: utf-8 -*-
r"""BG8 읽기·쓰기(2026-10-31) — 512 B 팔레트 + u16 칸 폭·칸 높이·타일 수·8 + u16 맵(칸 폭×높이, 타일 번호) + 타일 8×8 8비트
  load(d) → (색번호 배열 H×W, 머리 정보) · save(d, arr) → 고친 칸만 타일을 바꿈(그 타일을 다른 칸도 쓰면 새 타일 덧붙임, 같은 그림 타일 있으면 재사용)"""
import struct
import numpy as np


def load(d):
    cw, ch, nt, x = struct.unpack_from('>4H', d, 0x200)
    mo = 0x208; to = mo + 2 * cw * ch
    mp = np.array(struct.unpack_from('>%dH' % (cw * ch), d, mo)).reshape(ch, cw)
    tiles = np.frombuffer(d[to:to + 64 * nt], np.uint8).reshape(nt, 8, 8)
    a = np.zeros((ch * 8, cw * 8), int)
    for y in range(ch):
        for xx in range(cw): a[y * 8:y * 8 + 8, xx * 8:xx * 8 + 8] = tiles[mp[y, xx]]
    return a, (cw, ch, nt, x, mp, tiles)


def save(d, arr):
    old, (cw, ch, nt, x, mp, tiles) = load(d)
    tiles = [t.copy() for t in tiles]; mp = mp.copy()
    use = {}
    for y in range(ch):
        for xx in range(cw): use.setdefault(mp[y, xx], []).append((y, xx))
    look = {t.tobytes(): i for i, t in enumerate(tiles)}
    changed = 0
    for y in range(ch):
        for xx in range(cw):
            new = arr[y * 8:y * 8 + 8, xx * 8:xx * 8 + 8].astype(np.uint8)
            if (new == old[y * 8:y * 8 + 8, xx * 8:xx * 8 + 8]).all(): continue
            changed += 1; key = new.tobytes()
            if key in look: mp[y, xx] = look[key]; continue
            t = mp[y, xx]
            if len(use[t]) == 1: tiles[t] = new; look[key] = t
            else:
                tiles.append(new); mp[y, xx] = len(tiles) - 1; look[key] = len(tiles) - 1
    out = bytearray(d[:0x200]) + struct.pack('>4H', cw, ch, len(tiles), x) + struct.pack('>%dH' % (cw * ch), *mp.ravel()) + b''.join(t.tobytes() for t in tiles)
    return bytes(out), changed, len(tiles) - nt


def pal(d):
    return [((v & 31) * 8, (v >> 5 & 31) * 8, (v >> 10 & 31) * 8) for v in struct.unpack_from('>256H', d, 0)]
