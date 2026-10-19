# 두온 POD 종이책 펼침 표지 조립 — 뒷날개 | 뒷표지 | 책등 | 앞표지 | 앞날개 (사방 재단 여유 3mm)
#  기본 용지(2026-10-14 이신우 확정): 표지 아르떼 210g 날개 표지 / 내지 백색모조 100g / 무선제본 / 컬러
#  책등 = 내지 장수(쪽수÷2) × 내지 1장 두께 + 표지 두께 2장  → 0.5mm 단위 반올림 (인쇄소 값을 받으면 spine_mm 로 덮어쓴다)
#  사용: python pod_spread.py spread.json      (예시·키 설명: references/pod-cover.md)
#  출력: <out>.pdf (인쇄용, 벡터·글꼴 포함, 선 없음) · <out>.png (300dpi) · <out>_가이드.png (접는 선·재단선·안전 여백 표시, 확인용)
import os, sys, json, fitz

MM = 72 / 25.4
PAPER = {"백색모조100": 0.12, "백색모조80": 0.10, "미색모조100": 0.12, "미색모조80": 0.10, "아르떼210": 0.25}
FONT_DIRS = ["C:/Windows/Fonts/", os.path.expanduser("~/bookforge/assets/fonts/")]
FONTS = {"kb": "KoPubDotumBold.ttf", "km": "KoPubDotumMedium.ttf", "kl": "KoPubDotumLight.ttf"}


def font_path(name):
    for d in FONT_DIRS:
        if os.path.exists(d + name): return d + name
    raise SystemExit("글꼴 없음: " + name)

FP = {k: font_path(v) for k, v in FONTS.items()}
FO = {k: fitz.Font(fontfile=v) for k, v in FP.items()}
col = lambda c: tuple(v / 255 for v in c)


def spine_mm(c):
    if c.get("spine_mm"): return float(c["spine_mm"])
    inner = PAPER[c.get("inner_paper", "백색모조100")]
    cover = PAPER[c.get("cover_paper", "아르떼210")]
    raw = c["pages"] / 2 * inner + 2 * cover
    return round(raw * 2) / 2


def fonts(pg):
    for k, v in FP.items(): pg.insert_font(fontname=k, fontfile=v)

def wrap(s, f, size, width):
    out, cur = [], ""
    for w in s.split(" "):
        t = (cur + " " + w).strip()
        if FO[f].text_length(t, fontsize=size) <= width or not cur: cur = t
        else: out.append(cur); cur = w
    return out + [cur]

def put(pg, x, y, s, f, size, color, align="l"):
    w = FO[f].text_length(s, fontsize=size)
    x = x - w if align == "r" else x - w / 2 if align == "c" else x
    pg.insert_text((x, y), s, fontname=f, fontsize=size, color=color)


def place(pg, rect, src, trim=True):
    """src: 154×216(재단 여유 포함) 표지 PNG/PDF. 좌우 재단 여유를 잘라 표지 칸에 놓는다(위아래 여유는 그대로 씀)."""
    b = 3 * MM
    if src.lower().endswith(".pdf"):
        d = fitz.open(src); r = d[0].rect
        clip = fitz.Rect(b, 0, r.width - b, r.height) if trim else r
        pg.show_pdf_page(rect, d, 0, clip=clip, keep_proportion=False)
    else:
        from PIL import Image
        im = Image.open(src); w, h = im.size; k = w / (154 * MM)
        im = im.crop((round(b * k), 0, w - round(b * k), h)) if trim else im
        tmp = src + ".crop.png"; im.save(tmp); pg.insert_image(rect, filename=tmp, keep_proportion=False); os.remove(tmp)


def spine(doc, c, S, H):
    """책등을 가로 띠(길이 H, 폭 S)로 그린 뒤 돌려 붙인다 — 글자는 위에서 아래로 읽힌다."""
    sp = c["spine"]; tmp = fitz.open(); pg = tmp.new_page(width=H, height=S); fonts(pg)
    pg.draw_rect(pg.rect, fill=col(sp["bg"]), width=0)
    mid = S / 2; L, R = 3 * MM + 14 * MM, H - 3 * MM - 12 * MM
    ts = min(sp.get("title_pt", 11), S * 0.42)
    base = mid + ts * 0.36
    x = L
    put(pg, x, base, sp["title"], "kb", ts, col(sp["fg"])); x += FO["kb"].text_length(sp["title"], fontsize=ts) + 5 * MM
    if sp.get("sub"):
        ss = ts * 0.62
        put(pg, x, mid + ss * 0.36, sp["sub"], "kl", ss, col(sp.get("sub_fg", sp["fg"])))
    a = sp.get("authors", ""); as_ = ts * 0.7
    put(pg, R - 26 * MM, mid + as_ * 0.36, a, "km", as_, col(sp["fg"]), align="r")
    put(pg, R, mid + as_ * 0.36, sp.get("publisher", "두온교육"), "kb", as_, col(sp.get("accent", sp["fg"])), align="r")
    return tmp


def flap(pg, rect, fl, bg):
    pg.draw_rect(rect, fill=col(bg), width=0)
    L = rect.x0 + fl.get("pad_mm", 9) * MM; R = rect.x1 - fl.get("pad_mm", 9) * MM
    y = rect.y0 + 3 * MM + 22 * MM
    fg, mist, acc = col(fl.get("fg", [255, 255, 255])), col(fl.get("mist", [196, 208, 222])), col(fl.get("accent", [247, 148, 30]))
    if fl.get("heading"):
        put(pg, L, y, fl["heading"], "kb", 9, acc); pg.draw_rect(fitz.Rect(L, y + 5, L + 20, y + 7), fill=acc, width=0); y += 22
    for item in fl.get("items", []):
        if isinstance(item, str):
            for s in wrap(item, "kl", 7.6, R - L): put(pg, L, y, s, "kl", 7.6, mist); y += 12
            y += 6; continue
        name, body = item
        put(pg, L, y, name, "kb", 8.6, fg); y += 12.5
        for s in wrap(body, "kl", 7.2, R - L): put(pg, L, y, s, "kl", 7.2, mist); y += 11
        y += 8
    if fl.get("foot"):
        yb = rect.y1 - 3 * MM - 14 * MM
        for s in reversed(fl["foot"]): put(pg, L, yb, s, "km", 7.6, mist); yb -= 12


def build(c):
    B, TW, TH = 3, c.get("trim", [148, 210])[0], c.get("trim", [148, 210])[1]
    F = c.get("flap_mm", 100); S = spine_mm(c)
    xs = [B, B + F, B + F + TW, B + F + TW + S, B + F + 2 * TW + S, B + 2 * F + 2 * TW + S]   # 접는 선·재단선 (mm)
    Wmm, Hmm = xs[-1] + B, TH + 2 * B
    doc = fitz.open(); pg = doc.new_page(width=Wmm * MM, height=Hmm * MM); fonts(pg)
    R = lambda x0, x1: fitz.Rect(x0 * MM, 0, x1 * MM, Hmm * MM)
    bg = c["spine"]["bg"]
    flap(pg, R(0, xs[1]), c.get("back_flap", {}), c.get("flap_bg", bg))          # 뒷날개 (왼쪽 재단 여유 포함)
    place(pg, R(xs[1], xs[2]), c["back"])                                           # 뒷표지
    sp = spine(doc, c, S * MM, Hmm * MM)
    pg.show_pdf_page(R(xs[2], xs[3]), sp, 0, rotate=-90)                            # 책등
    place(pg, R(xs[3], xs[4]), c["front"])                                          # 앞표지
    flap(pg, R(xs[4], Wmm), c.get("front_flap", {}), c.get("flap_bg", bg))         # 앞날개
    doc.subset_fonts()
    out = c["out"]; doc.save(out + ".pdf", garbage=3, deflate=True)
    pix = pg.get_pixmap(dpi=300); pix.save(out + ".png")
    # 확인용 가이드 (인쇄 파일에는 선을 넣지 않는다)
    g = fitz.open(out + ".pdf"); gp = g[0]
    for x in xs: gp.draw_line((x * MM, 0), (x * MM, Hmm * MM), color=(1, 0, 1) if x in (xs[0], xs[-1]) else (0, 1, 1), width=0.6, dashes="[4 3] 0")
    for y in (B, Hmm - B): gp.draw_line((0, y * MM), (Wmm * MM, y * MM), color=(1, 0, 1), width=0.6, dashes="[4 3] 0")
    for a, b in ((xs[1], xs[2]), (xs[3], xs[4])):
        gp.draw_rect(fitz.Rect((a + 5) * MM, (B + 5) * MM, (b - 5) * MM, (Hmm - B - 5) * MM), color=(1, 0.5, 0), width=0.5)
    gp.get_pixmap(dpi=60).save(out + "_가이드.png")
    print("책등 %.1fmm (내지 %d쪽 · %s / 표지 %s) | 펼침면 %.1f × %.1f mm (재단 후 %.1f × %d)" % (
        S, c["pages"], c.get("inner_paper", "백색모조100"), c.get("cover_paper", "아르떼210"), Wmm, Hmm, Wmm - 2 * B, TH))
    print("접는 선(mm, 왼쪽 끝 기준):", ", ".join("%.1f" % x for x in xs[1:-1]))
    return S


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[1])))
    build(cfg)
