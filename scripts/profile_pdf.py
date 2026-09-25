#!/usr/bin/env python3
"""원고 PDF 구조 프로파일 — book.json "manuscript" 설정값(sizes·full_x1·skip_pages)을 정하기 위한 실측.

사용: python3 profile_pdf.py <원고.pdf> [출력.txt]
출력(UTF-8 파일, 콘솔 cp949 깨짐 방지): 판형, 급수×굵기별 글자수·예시 3개, 본문 급수의 줄 끝 x1 분포,
글머리표 후보 글리프, 표 수, 쪽별 첫 줄. 이 결과로 급수 역할을 배정한다:
  가장 큰 Bold(장 제목) → chapter / 부 제목 → part / 절 제목 → section /
  글자수 최다 Regular → body / 들여쓴 작은 급수(프롬프트) → panel / 참고자료 급수 → ref /
  쪽마다 같은 문구가 반복되는 가장 작은 급수 → running_head
full_x1 = 본문 줄 끝 x1 분포에서 '꽉 찬 줄' 무리의 하단보다 조금 낮게(예: 541~551 무리면 530).
"""
import collections
import sys
from pathlib import Path

import pymupdf

src = Path(sys.argv[1])
out_p = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name("_profile.txt")
d = pymupdf.open(src)
L = [f"파일: {src.name} | {d.page_count}쪽 | 판형 {d[0].rect.width / 72 * 25.4:.1f}×{d[0].rect.height / 72 * 25.4:.1f}mm"]
chars = collections.Counter()
examples = collections.defaultdict(list)
x1s = collections.defaultdict(collections.Counter)
glyphs = collections.Counter()
tables = 0
first_lines = []
for i, p in enumerate(d):
    try:
        tables += len(p.find_tables().tables)
    except Exception:
        pass
    first = None
    for b in p.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for ln in b["lines"]:
            sp = [s for s in ln["spans"] if s["text"].strip()]
            if not sp:
                continue
            t = "".join(s["text"] for s in sp)
            size = round(max(s["size"] for s in sp), 1)
            bold = any("Bold" in s["font"] for s in sp)
            key = (size, "B" if bold else "R")
            chars[key] += len(t)
            if len(examples[key]) < 3:
                examples[key].append(f"p{i + 1} x0={ln['bbox'][0]:.0f}: {t[:40]}")
            x1s[size][round(ln["bbox"][2])] += 1
            if len(t.strip()) == 1 and not t.strip().isalnum():
                glyphs[(t.strip(), sp[0]["font"])] += 1
            if first is None:
                first = f"p{i + 1}: [{size}{'B' if bold else ''}] {t[:40]}"
    first_lines.append(first or f"p{i + 1}: (텍스트 없음)")
L.append("\n== 급수·굵기별 글자수 (많은 순) ==")
for key, n in chars.most_common():
    L.append(f"{key[0]:>5}pt {key[1]}  {n:>7,}자")
    L += ["        " + e for e in examples[key]]
body = max(chars, key=chars.get)[0]
L.append(f"\n== 본문 추정 {body}pt 줄 끝 x1 분포 (상위 15) ==")
L.append(", ".join(f"{x}:{c}" for x, c in sorted(x1s[body].items(), key=lambda kv: -kv[1])[:15]))
L.append("\n== 한 글자 기호(글머리표 후보) ==")
L += [f"{repr(g)} {f} ×{c}" for (g, f), c in glyphs.most_common(8)]
L.append(f"\n표 {tables}개")
L.append("\n== 쪽별 첫 줄 (표지·목차 쪽 = skip_pages 후보) ==")
L += first_lines
out_p.write_text("\n".join(L), encoding="utf-8")
print(f"OK {out_p}")
