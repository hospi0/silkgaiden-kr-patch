# -*- coding: utf-8 -*-
"""번역 TSV 만들기(2026-10-31) → my files/tsv/ — 18KB 단위(자투리 1/3 미만은 앞 파일에 합침)
  sg_###.tsv = 대본 본문(같은 글 하나로, 위치 = 처음 기록 ID(×같은 글 수)) · sg_sys_###.tsv = 코드 파일 문자열(위치 = 파일:16진 위치(바이트 예산))
  JP 토큰: ／ 줄바꿈 · {1}{2}… 긴 제어(번호 그대로 둘 것) · @K @P @. @Q1 @} @= @< @/ @B @C @pW 등 그대로
  python tools/mk_tsv.py"""
import csv, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 18 * 1024
OUT = os.path.join(ROOT, 'my files', 'tsv')


def write(prefix, lines):
    head = '번호\t위치\tJP\tKO\n'; chunks = [[]]; size = len(head.encode())
    for ln in lines:
        b = len(ln.encode())
        if chunks[-1] and size + b > LIMIT: chunks.append([]); size = len(head.encode())
        chunks[-1].append(ln); size += b
    if len(chunks) > 1 and sum(len(l.encode()) for l in chunks[-1]) < LIMIT // 3: chunks[-2] += chunks.pop()
    for i, c in enumerate(chunks):
        p = os.path.join(OUT, '%s_%03d.tsv' % (prefix, i + 1))
        open(p, 'w', encoding='utf-8', newline='\n').write(head + ''.join(c))
        print(os.path.basename(p), len(c), '줄', os.path.getsize(p), 'B')


def main():
    sys.stdout.reconfigure(encoding='utf-8'); os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'script.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
    cnt = {}
    for r in rows:
        k = r['같은글'] or r['ID']; cnt[k] = cnt.get(k, 0) + 1
    uniq = [r for r in rows if not r['같은글']]
    write('sg', ['%05d\t%s(×%d)\t%s\t\n' % (n + 1, r['ID'], cnt[r['ID']], r['JP']) for n, r in enumerate(uniq)])
    srows = list(csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'sys.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
    write('sg_sys', ['S%04d\t%s:%s(%sB)\t%s\t\n' % (n + 1, r['파일'], r['위치'], r['바이트'], r['JP']) for n, r in enumerate(srows)])


if __name__ == '__main__':
    main()
