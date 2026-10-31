# -*- coding: utf-8 -*-
r"""이름 입력 한글화(2026-10-31) — XCHK(오버레이) 0x17C~ 이름판 칸 = 4 B(SJIS 한 글자 + NUL 채움, 「カナ」「かな」 = 4 B 꽉, 「END」 3 B + NUL)
  히라 판 0x17C~0x27B(70칸 = 10열×7줄: あかさたなはまやらわ / いきし… / … / ぁぃぅぇぉ゛゜☆カナ / ゃゅょっ・－～END)
  가타 판 0x27C~0x35F(ア… / ァィゥェォ / かな / ャュョッ — ゛゜☆·・－～END 는 히라 판 것을 같이 쓰는 듯)
  이름 = SJIS 로 저장 → 대사 @P 로 찍힘 ⇒ 한글 음절은 넣기 빌더의 글꼴 배정(빈 한자 코드)과 같은 표로 SJIS 바꿈
  한글: 가나 칸(히라 55 = あ~ん·ぁぃぅぇぉ·ゃゅょっ / 가타 55 = ア~ン·ァィゥェォ·ャュョッ) → 음절 110(가나다순) · 「カナ」→「다음」 「かな」→「이전」 · ・－～·END 그대로
  ゛゜☆ 칸은 그대로(두 판이 같이 쓰는 듯) — 탁점 처리(0x3B8 변환표)는 한글엔 안 걸림(표에 없는 글자)
  patch(xchk, enc) — enc = 한글 글자열 → SJIS 바이트(빌더의 encode) · python tools/nameentry.py → 미리보기 work/shot/name_preview.png"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYL = ('가경고구그기김나남노누니다단대도동두드라란레로루리린마만메모무문미민바박반배보부브비빈사서선성세소수스시신실아'
       '안야양연영오온우운원유윤은의이인일자장재전정제조주준지진차천철초최카코크키타태토트티파프피하한해현호화환훈희히')
HIRA = 0x17C; KATA = 0x27C
HIRA_KANA = 'あかさたなはまやらわいきしちにひみりうくすつぬふむゆるをえけせてねへめれおこそとのほもよろんぁぃぅぇぉゃゅょっ'   # ゛゜☆ 는 가타 판과 같이 씀 → 그대로
KATA_KANA = 'アカサタナハマヤラワイキシチニヒミリウクスツヌフムユルヲエケセテネヘメレオコソトノホモヨロンァィゥェォャュョッ'


def cells(d, start, end):
    """(위치, 글자) — 4 B 칸"""
    out = []
    for o in range(start, end, 4):
        b = d[o:o + 4].split(b'\0')[0]
        out.append((o, b.decode('cp932', 'replace')))
    return out


def plan(d):
    """바꿀 칸 → 새 글자. 원래 가나 차례대로(줄 먼저) 음절을 채움"""
    assert len(SYL) == len(set(SYL)) and list(SYL) == sorted(SYL), '음절 중복·순서'
    rep = {}; k = 0
    for start, end, kana in ((HIRA, KATA, HIRA_KANA), (KATA, 0x360, KATA_KANA)):
        for o, ch in cells(d, start, end):
            if ch in kana and len(ch) == 1:
                rep[o] = SYL[k] if k < len(SYL) else None; k += 1
            elif ch == 'カナ': rep[o] = '다음'
            elif ch == 'かな': rep[o] = '이전'
    assert k == len(HIRA_KANA) + len(KATA_KANA) == 110, k
    assert len(SYL) == 110, len(SYL)
    return rep


def patch(d, enc):
    d = bytearray(d)
    for o, t in plan(bytes(d)).items():
        b = enc(t); assert len(b) <= 4, (hex(o), t)
        d[o:o + 4] = b + bytes(4 - len(b))
    return bytes(d)


def layout(page):
    """메모리 칸 차례 → 화면 (줄, 열) — 화면 8·9(받은 스테이트): い·え 줄은 や·わ 열(7·9) 빔, 6줄 끝 판 바꾸기는 8열(2칸 폭)"""
    pos = []
    for r in range(5):
        for c in range(10):
            if r in (1, 3) and c in (7, 9): continue
            pos.append((r, c))
    if page == 0:
        pos += [(5, c) for c in range(9)] + [(6, c) for c in range(8)]
    else:
        pos += [(5, c) for c in range(5)] + [(5, 8)] + [(6, c) for c in range(4)]
    return pos


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = open(os.path.join(ROOT, 'work', 'arc', 'XCHK'), 'rb').read(); rep = plan(d)
    f = ImageFont.truetype(os.path.join('C:' + os.sep, 'Windows', 'Fonts', 'malgun.ttf'), 18)
    S = Image.new('RGB', (2 * 10 * 34 + 40, 7 * 30 * 2 + 70), (40, 40, 110)); dr = ImageDraw.Draw(S)
    for pi, (start, end) in enumerate(((HIRA, KATA), (KATA, 0x360))):
        cs = [(o, ch) for o, ch in cells(d, start, end) if ch]           # 빈 칸(「カナ」 뒤 등)은 화면 자리 안 차지
        pos = layout(pi)
        for i, (o, ch) in enumerate(cs):
            if i >= len(pos): continue
            r, c = pos[i]; x = 10 + c * 34; y = 10 + pi * 225 + r * 30
            dr.text((x, y), ch, font=f, fill=(200, 200, 200))
            dr.text((x + 10 * 34 + 20, y), rep.get(o, ch) or '', font=f, fill=(255, 255, 255))
    S.save(os.path.join(ROOT, 'work', 'shot', 'name_preview.png'))
    print('음절 %d · 칸 %d → work/shot/name_preview.png' % (len(SYL), len(rep)))


if __name__ == '__main__':
    main()
