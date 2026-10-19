"""[템플릿 — 황혜진 책 tools/pod_cover.py 사본. SRC_*·SPINE_RGB·BARCODE_AT·SRC·INNER 를 책마다 실측값으로 바꾼다]
디자이너 펼침 표지(../1.pdf)를 인쇄 규격 펼침면으로 다시 조립한다.

디자이너 파일은 앞·뒤표지를 재단 여유 포함 154mm 낱면 그대로 이어 붙여(519.1×215.9mm)
접는 자리 안쪽에 재단 여유 3mm 씩이 남아 있다. 이를 잘라 내고 완성 규격으로 다시 놓는다.

  재단 3 | 뒷날개 100 | 뒷표지 148 | 책등 S | 앞표지 148 | 앞날개 100 | 재단 3   × 216
  S = 내지 쪽수 / 2 × 0.12 + 0.5mm → 0.5mm 반올림 (인쇄소 값이 있으면 --spine)

뒷표지에 바코드+정가(tools/barcode.typ)를 얹는다. ISBN 이 없으면 바코드 자리 상자.

  python tools/pod_cover.py [--isbn 9791124020NNN --addon 03810] [--price 15,000] [--spine 10.5] OUT.pdf
"""
import argparse
import subprocess
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent.parent
SRC = HERE.parent / "1.pdf"
INNER = HERE.parent / "황혜진_공부가되는아이곁에는어른이있었다_POD내지_154x216.pdf"
MM = 72 / 25.4
BLEED, FLAP, TRIM_W, H = 3.0, 100.0, 148.0, 216.0
SPINE_RGB = (0.0, 0.21768520772457123, 0.16585031151771545)   # 디자이너 책등 바탕색

# 디자이너 파일의 칸 경계(mm, 실측): 뒷날개 0~99.95 | 뒷표지 99.95~253.88 | 책등 ~264.05 | 앞표지 ~418.85 | 앞날개 ~519.1
SRC_BACK = (99.95 + BLEED, 253.88 - BLEED)
SRC_SPINE = (253.88, 264.05)
SRC_FRONT = (264.05 + BLEED, 418.85 - BLEED)
SRC_BFLAP = (0.0, 99.95)
SRC_FFLAP = (418.85, 519.11)
SRC_H = 215.9

# 뒷표지 낱면(재단 여유 포함) 왼쪽 위에서 잰 바코드 위치 — 추천사 아래 빈 녹색 면
BARCODE_AT = (10.5, 135.0)


def spine_mm(pages):
    return round((pages / 2 * 0.12 + 0.5) * 2) / 2


def place(out, src, sx, dx0, dx1):
    """src 의 가로 구간 sx 를 out 의 dx0~dx1 에 세로 꽉 차게 놓는다."""
    clip = fitz.Rect(sx[0] * MM, 0, sx[1] * MM, SRC_H * MM)
    out.show_pdf_page(fitz.Rect(dx0 * MM, 0, dx1 * MM, H * MM), src, 0, clip=clip, keep_proportion=False)


def barcode_pdf(args, tmp):
    cmd = ["typst", "compile", "--root", str(HERE), "--font-path", str(Path.home() / "bookforge/assets/fonts"),
           "--ignore-system-fonts", "--input", f"price={args.price}"]
    if args.isbn:
        cmd += ["--input", f"isbn={args.isbn}", "--input", f"addon={args.addon}"]
    subprocess.run(cmd + [str(HERE / "tools/barcode.typ"), str(tmp)], check=True)
    return fitz.open(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--isbn")
    ap.add_argument("--addon", default="03810")
    ap.add_argument("--price", default="15,000")
    ap.add_argument("--spine", type=float)
    args = ap.parse_args()

    pages = len(fitz.open(INNER))
    S = args.spine or spine_mm(pages)
    x_bflap = BLEED
    x_back = x_bflap + FLAP
    x_spine = x_back + TRIM_W
    x_front = x_spine + S
    x_fflap = x_front + TRIM_W
    W = x_fflap + FLAP + BLEED

    src = fitz.open(SRC)
    doc = fitz.open()
    pg = doc.new_page(width=W * MM, height=H * MM)
    pg.draw_rect(pg.rect, color=None, fill=(1, 1, 1))

    place(pg, src, SRC_BFLAP, x_bflap, x_back)
    place(pg, src, SRC_FFLAP, x_fflap, x_fflap + FLAP)
    pg.draw_rect(fitz.Rect(x_spine * MM, 0, x_front * MM, H * MM), color=None, fill=SPINE_RGB)
    sw = SRC_SPINE[1] - SRC_SPINE[0]                       # 책등 글자는 늘이지 않고 가운데
    sx0 = x_spine + (S - sw) / 2
    place(pg, src, SRC_SPINE, sx0, sx0 + sw)
    place(pg, src, SRC_BACK, x_back, x_spine)
    place(pg, src, SRC_FRONT, x_front, x_fflap)

    bc = barcode_pdf(args, HERE / "qc/_barcode.pdf")
    r = bc[0].rect
    bx = x_back - BLEED + BARCODE_AT[0]
    by = BARCODE_AT[1]
    pg.show_pdf_page(fitz.Rect(bx * MM, by * MM, bx * MM + r.width, by * MM + r.height), bc, 0)

    trim = fitz.Rect(BLEED * MM, BLEED * MM, (W - BLEED) * MM, (H - BLEED) * MM)
    pg.set_trimbox(trim)
    pg.set_bleedbox(pg.rect)
    doc.set_metadata({"title": "공부가 되는 아이 곁에는 어른이 있었다 — POD 펼침 표지", "author": "황혜진",
                      "subject": f"펼침 {W:.1f}×{H:.0f}mm, 책등 {S}mm(내지 {pages}쪽), 날개 {FLAP:.0f}mm"})
    doc.save(args.out, garbage=3, deflate=True)
    print(f"{args.out}: {W:.1f}×{H:.0f}mm  책등 {S}mm(내지 {pages}쪽)  "
          f"접는 선 x={x_back:.1f}/{x_spine:.1f}/{x_front:.1f}/{x_fflap:.1f}mm  바코드 {'ISBN ' + args.isbn if args.isbn else '자리만'}")
    return W, S, (x_back, x_spine, x_front, x_fflap)


if __name__ == "__main__":
    main()
