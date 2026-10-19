"""줄넘침 점검: 판면 오른쪽 여백을 넘은 글줄, 표 칸 안에서 1~2글자만 떨어진 줄(음절 중간 줄바꿈 의심),
판면 아래로 흘러내린 글줄을 찾아 목록으로 낸다.

정상 양끝맞춤 줄도 글리프 상자 때문에 오른쪽 경계를 +2.8pt(따옴표·마침표로 끝나면 +5.2pt) 넘게
잡히므로, 6pt 를 넘는 것만 넘침으로 센다.

사용: python tools/overflow_check.py <책.pdf> <보고서.txt>
"""
import sys

import pymupdf

MM = 72 / 25.4
RIGHT_MARGIN, BOTTOM_MARGIN = 14 * MM, 17 * MM
RIGHT_SLACK = 6.0
TABLE_SIZES = (7.6, 8.4)

doc = pymupdf.open(sys.argv[1])
out = []
n_over = n_frag = n_low = 0
for pno, page in enumerate(doc, 1):
    W, H = page.rect.width, page.rect.height
    tlines = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            spans = [s for s in ln["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans).strip()
            x1 = max(s["bbox"][2] for s in spans)
            y1 = max(s["bbox"][3] for s in spans)
            size = round(spans[0]["size"], 1)
            if pno > 1 and x1 > W - RIGHT_MARGIN + RIGHT_SLACK:
                n_over += 1
                out.append(f"p{pno} 오른쪽 넘침 {x1 - (W - RIGHT_MARGIN):+.1f}pt: {text[:70]}")
            if pno > 1 and size > 8.1 and y1 > H - BOTTOM_MARGIN + 2:
                n_low += 1
                out.append(f"p{pno} 아래 넘침: {text[:70]}")
            if size in TABLE_SIZES:
                tlines.append((ln["bbox"][0], ln["bbox"][1], ln["bbox"][3], size, text))
    # 표 칸 조각 줄: 1~2글자 줄이 같은 칸(같은 x0) 바로 윗줄에 붙어 있으면 줄바꿈으로 떨어진 조각
    for x0, y0, y1, size, text in tlines:
        if len(text.replace(" ", "")) > 2:
            continue
        if any(abs(px0 - x0) < 1.0 and 0 <= y0 - py1 < 3.0 for px0, _, py1, _, _ in tlines):
            n_frag += 1
            out.append(f"p{pno} 표 칸 조각 줄 [{size}pt]: {text!r}")
summary = f"오른쪽 넘침 {n_over} · 아래 넘침 {n_low} · 표 칸 조각 줄 {n_frag} (총 {doc.page_count}쪽)"
with open(sys.argv[2], "w", encoding="utf-8") as f:
    f.write(summary + "\n" + "\n".join(out) + "\n")
print(summary)
