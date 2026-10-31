# -*- coding: utf-8 -*-
"""ARC.AKV 묶음 풀기(2026-10-31) — ARC.IND = 20 B 항목(이름 12 B NUL 채움 · 위치 u32 BE(AKV 안 바이트) · 크기 u32 BE)
  python tools/akv.py → work/arc/<이름> + 목록"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def index(ind):
    out = []
    for k in range(0, len(ind) - 19, 20):
        nm = ind[k:k + 12].split(b'\0')[0].decode('ascii', 'replace'); o, s = struct.unpack_from('>II', ind, k + 12)
        if nm: out.append((nm, o, s))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ind = open(os.path.join(ROOT, 'work', 'disc0', 'ARC.IND'), 'rb').read()
    akv = open(os.path.join(ROOT, 'work', 'disc0', 'ARC.AKV'), 'rb').read()
    od = os.path.join(ROOT, 'work', 'arc'); os.makedirs(od, exist_ok=True)
    ix = index(ind)
    for nm, o, s in ix: open(os.path.join(od, nm), 'wb').write(akv[o:o + s])
    print(len(ix), '항목 · 끝', hex(max(o + s for _, o, s in ix)), '/ AKV', hex(len(akv)))


if __name__ == '__main__':
    main()
