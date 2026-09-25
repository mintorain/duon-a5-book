#!/usr/bin/env python3
"""PDF 전체를 18면씩(6×3) 한 장에 모은 검수용 몽타주 PNG. 쪽 나눔·빈 면·간지 흐름 확인용.

사용: python3 montage.py <책.pdf> <출력폴더> [--pages 1,2,5]   (--pages 면 그 면들만 한 줄로 크게)
show_pdf_page 로 합성한다(Pixmap.copy 합성은 첫 면만 찍히는 문제가 있었다).
"""
import sys
from pathlib import Path

import pymupdf

src = pymupdf.open(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
n = src.page_count
pw, ph = src[0].rect.width, src[0].rect.height
gap = 8
if "--pages" in sys.argv:
    pages = [int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")]
    doc = pymupdf.open()
    pg = doc.new_page(width=len(pages) * (pw + gap) + gap, height=ph + 2 * gap)
    pg.draw_rect(pg.rect, color=None, fill=(0.78, 0.78, 0.78))
    for k, p in enumerate(pages):
        x = gap + k * (pw + gap)
        pg.show_pdf_page(pymupdf.Rect(x, gap, x + pw, gap + ph), src, p - 1)
        pg.insert_text((x + 4, gap + 14), str(p), fontsize=11, color=(1, 0, 0))
    pg.get_pixmap(matrix=pymupdf.Matrix(0.9, 0.9)).save(out / "pages.png")
    print(f"OK {out / 'pages.png'}")
    sys.exit(0)
cols, rows = 6, 3
per = cols * rows
doc = pymupdf.open()
for s in range((n + per - 1) // per):
    pg = doc.new_page(width=cols * (pw + gap) + gap, height=rows * (ph + gap) + gap)
    pg.draw_rect(pg.rect, color=None, fill=(0.8, 0.8, 0.8))
    for k in range(per):
        p = s * per + k
        if p >= n:
            break
        x = gap + (k % cols) * (pw + gap)
        y = gap + (k // cols) * (ph + gap)
        pg.show_pdf_page(pymupdf.Rect(x, y, x + pw, y + ph), src, p)
        pg.insert_text((x + 4, y + 14), str(p + 1), fontsize=11, color=(1, 0, 0))
for i, pg in enumerate(doc):
    pg.get_pixmap(matrix=pymupdf.Matrix(0.45, 0.45)).save(out / f"sheet{i + 1}.png")
print(f"OK {doc.page_count}장 → {out}")
