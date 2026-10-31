# -*- coding: utf-8 -*-
r"""드래곤 마스터 실크 외전 디스크 빌드(2026-10-31, 링클 tools/discbuild.py 를 옮김) — 원본 트랙 1 사본에 바꾼 파일을 쓰고 MODE1 EDC/ECC 재계산.
  바꾼 파일: work/build/ 아래(디스크 경로 그대로 — tools/poc.py 결과: ARC.AKV·ARC.IND)
  크기: 원래 섹터 안이면 제자리, 넘치면 «고정 자리» SLOT(LBA 38270 = 마지막 파일 ENDING/ENDBAK.BIN 끝 38267 뒤, 트랙 끝 빈 300섹터 38267~38566) — 트랙 파일 크기·음악 트랙 위치 안 바뀜.
        고정 자리라 빌드마다 같은 LBA(옛 시험본 스테이트 호환). 넘치면 중단.
  출력: dist/build/<디스크 이름>/ (트랙 1 패치본 + 원본 트랙 2·cue 복사), 되읽어 검산.
  python tools/discbuild.py                 → 미리보기(자리 계산만, 아무것도 안 씀)
  python tools/discbuild.py --write [--disc 0,1,2,3] [--install]
    ⛔--write·--install 은 하스피 허락 받고. --install = F:\hospi\roms\ss roms\<디스크 이름>\ 트랙 1 덮어쓰기
"""
import hashlib, os, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc
from cdrom_ecc import recalc_sector

OUT = os.path.join(ROOT, 'dist', 'build')
F_DIR = r'F:\hospi\roms\ss roms'
SLOT = 130500                    # 트랙 1 끝 빈 섹터(마지막 파일 SGBN_CPY.TXT 130494 뒤 ~ 130644) — 이번엔 제자리만
FORCE_MOVE = set()
GROW = set()
IP_SIZE_OFF = 0xF4               # IP.BIN 1st read 크기(u32 BE) = 0.TSK 크기


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''):
            h.update(c)
    return h.hexdigest()


def changes(fs):
    """{디스크 안 경로: 바이트} — work/build 아래 파일 전부(tools/insert.py 결과), 디스크에 같은 경로가 있어야 함"""
    out = {}
    for dp, _, fn in os.walk(os.path.join(ROOT, 'work', 'build')):
        for f in fn:
            p = os.path.join(dp, f); rel = '/' + os.path.relpath(p, os.path.join(ROOT, 'work', 'build')).replace(os.sep, '/')
            if rel not in fs: sys.exit('⛔ 디스크에 없는 파일 %s' % rel)
            out[rel] = open(p, 'rb').read()
    return out


def dir_records(fh, lba, size, base='/'):
    out = {}
    for si in range((size + 2047) // 2048):
        fh.seek((lba + si) * 2352 + 16); d = fh.read(2048); p = 0
        while p < 2048:
            L = d[p]
            if L == 0:
                break
            el, sz, fl = struct.unpack_from('<I', d, p + 2)[0], struct.unpack_from('<I', d, p + 10)[0], d[p + 25]
            nm = d[p + 33:p + 33 + d[p + 32]]
            if nm not in (bytes([0]), bytes([1])):
                name = nm.decode('ascii', 'replace').split(';')[0]
                if fl & 2:
                    out.update(dir_records(fh, el, sz, base + name + '/'))
                else:
                    out[base + name] = (lba + si, p)
            p += L
    return out


def put_sector(fh, lba, data2048, template):
    sec = bytearray(template)
    m = lba + 150; mm, ss, ff = m // 4500, (m // 75) % 60, m % 75
    bcd = lambda x: (x // 10) << 4 | (x % 10)
    sec[12:16] = bytes([bcd(mm), bcd(ss), bcd(ff), 1])
    sec[16:2064] = data2048 + bytes(2048 - len(data2048))
    fh.seek(lba * 2352); fh.write(recalc_sector(bytes(sec)))


def patch_record(fh, rec, lba, size):
    rs, ro = rec
    fh.seek(rs * 2352); sec = bytearray(fh.read(2352))
    struct.pack_into('<I', sec, 16 + ro + 2, lba); struct.pack_into('>I', sec, 16 + ro + 6, lba)
    struct.pack_into('<I', sec, 16 + ro + 10, size); struct.pack_into('>I', sec, 16 + ro + 14, size)
    fh.seek(rs * 2352); fh.write(recalc_sector(bytes(sec)))


def plan(n):
    rom = disc.bin_path(n)
    fs = {p: (l, s) for p, l, s in disc.files(rom)}
    ch = changes(fs)
    tend = os.path.getsize(rom) // 2352
    assert max(l + (s + 2047) // 2048 for l, s in fs.values() if l < tend) <= SLOT     # SOUND1·3 = 음악 트랙 가리키는 항목
    sec_of = lambda b: (b + 2047) // 2048
    place = {}; end = SLOT
    movers = sorted(f for f, data in ch.items() if (len(data) > sec_of(fs[f][1]) * 2048 and f not in GROW) or f in FORCE_MOVE)
    for f in movers:
        place[f] = (end, '트랙 끝 고정 자리'); end += sec_of(len(ch[f]))
    for f in GROW:                                                        # 제자리에서 늘림 — 뒤 파일이 옮겨 비운 섹터까지
        if f in ch and len(ch[f]) > sec_of(fs[f][1]) * 2048:
            l = fs[f][0]; nxt = min(x for p, (x, s) in fs.items() if x > l and p not in movers)
            if l + sec_of(len(ch[f])) > nxt: sys.exit('⛔ %s 제자리 늘림 넘침 %d > %d' % (f, l + sec_of(len(ch[f])), nxt))
    if end > tend: sys.exit('⛔ 고정 자리 넘침 %d > %d' % (end, tend))
    return rom, fs, ch, place, tend


def build(n, write, install):
    rom, fs, ch, place, end = plan(n)
    name = disc.NAMES[n]
    print('디스크 %d: 바꿀 파일 %d · 트랙 1 섹터 %d (그대로)' % (n, len(ch), end))
    for f, data in ch.items():
        lba, size = fs[f]
        how = place.get(f, (lba, '제자리'))
        print('  %-14s %9d → %9d B · %s LBA %d' % (f, size, len(data), how[1], how[0]))
    if not write:
        return
    od = os.path.join(OUT, name); os.makedirs(od, exist_ok=True)
    src_dir = os.path.dirname(rom)
    for x in os.listdir(src_dir):
        if 'Track 1)' not in x and os.path.isfile(os.path.join(src_dir, x)):
            shutil.copyfile(os.path.join(src_dir, x), os.path.join(od, x))
    t1 = os.path.join(od, os.path.basename(rom))
    shutil.copyfile(rom, t1)
    newpos = {}
    with open(t1, 'r+b') as fh:
        fh.seek(16 * 2352); pvd = bytearray(fh.read(2352))
        rlba, rsz = struct.unpack_from('<I', pvd, 16 + 156 + 2)[0], struct.unpack_from('<I', pvd, 16 + 156 + 10)[0]
        recs = dir_records(fh, rlba, rsz)
        fh.seek(16 * 2352); template = fh.read(2352)
        for f, data in ch.items():
            lba, size = fs[f]
            if f not in place:
                wlba = lba; pad = data + bytes(max(0, size - len(data)))
            else:
                wlba = place[f][0]; pad = data
            nsec = (len(pad) + 2047) // 2048
            for i in range(nsec):
                chunk = pad[i * 2048:(i + 1) * 2048]
                if wlba == lba:
                    fh.seek((lba + i) * 2352); sec = bytearray(fh.read(2352))
                    if sec[16:16 + len(chunk)] == chunk:
                        continue
                    sec[16:16 + len(chunk)] = chunk
                    fh.seek((lba + i) * 2352); fh.write(recalc_sector(bytes(sec)))
                else:
                    put_sector(fh, wlba + i, chunk, template)
            if wlba != lba or len(data) != size:
                patch_record(fh, recs[f], wlba, len(data))
            newpos[f] = (wlba, len(data))
    if '/0.TSK' in ch:                                                    # IP.BIN 1st read 크기
        with open(t1, 'r+b') as fh:
            fh.seek(0); sec = bytearray(fh.read(2352))
            struct.pack_into('>I', sec, 16 + IP_SIZE_OFF, len(ch['/0.TSK']))
            fh.seek(0); fh.write(recalc_sector(bytes(sec)))
        print('  IP.BIN 1st read 크기 →', hex(len(ch['/0.TSK'])))
    fs2 = {p: (l, s) for p, l, s in disc.files(t1)}
    with open(t1, 'rb') as fh:
        for f, data in ch.items():
            l, s = fs2[f]
            assert (l, s) == newpos[f] and disc.sec(fh, l, (s + 2047) // 2048)[:s] == data, f
    assert os.path.getsize(t1) == os.path.getsize(rom), '트랙 크기 바뀜'
    m = md5(t1)
    print('  ✅트랙 1 md5 %s · 섹터 %d → %s' % (m, os.path.getsize(t1) // 2352, t1))
    if install:
        dst = os.path.join(F_DIR, name, os.path.basename(rom))
        shutil.copyfile(t1, dst)
        print('  F: 설치', '✅' if md5(dst) == m else '⛔ md5 불일치', dst)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    discs = [0]
    if '--disc' in sys.argv:
        discs = [int(x) for x in sys.argv[sys.argv.index('--disc') + 1].split(',')]
    for n in discs:
        build(n, '--write' in sys.argv, '--install' in sys.argv)


if __name__ == '__main__':
    main()
