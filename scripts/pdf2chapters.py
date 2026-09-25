#!/usr/bin/env python3
"""원고 PDF → bookforge 책 프로젝트 입력(chapters/*.md + outline.json). 원문 문장은 바꾸지 않는다.

사용: python3 pdf2chapters.py <book_dir>
설정: <book_dir>/book.json 의 "manuscript" 객체(값은 profile_pdf.py 결과를 보고 정한다)
  source          원고 PDF 경로(book_dir 기준 상대 또는 절대)
  skip_pages      건너뛸 쪽(표지·원고 목차 등, 1부터)
  sizes           급수 역할: chapter·part·section·panel·body·ref·running_head (pt, 소수 1자리)
  full_x1         본문 줄 끝 x1 이 이 값 이상이면 '꽉 찬 줄'(문단 계속)
  full_x1_ref     참고자료(ref 급수) 꽉 찬 줄 기준
  right_edge      판면 오른쪽 끝 x(라틴 단어 개행 판정용)
  panel_gap       패널 줄 사이 이 이상 벌어지면 패널 안 문단 구분(pt)
  para_gap        본문 줄 사이 이 이상이면 문단 경계(pt)
  bullet_glyph    글머리표 글리프(기본 OpenSymbol U+F0B7)
  prompt_title_regex  section 급수 중 이 패턴이면 '::: tip' 패널 제목으로
  part_regex      부 제목에서 부 번호를 뽑는 패턴
  author_title    저자 소개 장 제목(있으면 쪽번호 없는 앞부속 카드로 옮김)
  author_additions [[앞 항목, 추가 항목], ...] — 원고 밖 약력 추가(검증에서 제외)
  gift            {"title","lines":[...],"url"} 또는 null — 책 끝 QR 부속 면(assets/qr.png)
삭제: <book_dir>/deletions.json [{"text": 원문 그대로, ...}] — 문구마다 1회 이상 일치해야 하며,
      검증은 원문에서도 같은 문구를 빼고 대조한다(삭제 외 변경 0 보장).

변환 규칙: chapter→'# 장', part→'::: info PART NN'(다음 장 앞, 테마가 전면 간지로),
section→'## 절' 또는 '::: tip 실습 프롬프트 NN' 패널, panel→패널 안 한 줄=한 문단,
body→문단(꽉 찬 줄·라틴 단어 개행·문단 간격으로 이음/끊음), 글머리표+다음 줄→'- 항목',
ref→번호 목록, find_tables→GFM 표. 러닝헤드·폴리오는 버린다.
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

BOOK = Path(sys.argv[1]).resolve()
CFG = json.loads((BOOK / "book.json").read_text(encoding="utf-8"))["manuscript"]
_src = Path(CFG["source"])
SRC = _src if _src.is_absolute() else (BOOK / _src).resolve()
SKIP_PAGES = set(CFG.get("skip_pages", []))
SZ = {k: float(v) for k, v in CFG["sizes"].items()}
FULL_X1 = float(CFG.get("full_x1", 530))
FULL_X1_REF = float(CFG.get("full_x1_ref", FULL_X1 - 3))
RIGHT_EDGE = float(CFG.get("right_edge", FULL_X1 + 21))
PANEL_GAP = float(CFG.get("panel_gap", 24))
PARA_GAP = float(CFG.get("para_gap", 21))
BULLET = CFG.get("bullet_glyph", "")
PROMPT_H2_RE = re.compile(CFG.get("prompt_title_regex", r"^실습 프롬프트 \d+$"))
PART_RE = re.compile(CFG.get("part_regex", r"^(\d+)부\s"))
AUTHOR_TITLE = CFG.get("author_title", "저자 소개")
AUTHOR_ADDITIONS = [tuple(x) for x in CFG.get("author_additions", [])]
GIFT = CFG.get("gift")
_DEL_P = BOOK / "deletions.json"
DELETIONS = json.loads(_DEL_P.read_text(encoding="utf-8")) if _DEL_P.exists() else []

MD_LEAD_RE = re.compile(r"^(\d+\.\s|[-+*]\s|#|>)")
REF_ITEM_RE = re.compile(r"^\d{1,2}\.\s")
LATIN_TOKEN_RE = re.compile(r"^[A-Za-z0-9(\[\"'“‘#@%$&<]")


def is_size(it, role):
    return role in SZ and abs(it["size"] - SZ[role]) < 0.05


def latin_wrap(it, nxt):
    """짧게 끝난 줄이라도 다음 줄 첫 라틴/숫자 단어가 이 줄 끝에 들어갈 수 없었던 폭이면 단어 개행이다."""
    if nxt is None or nxt.get("kind") != "line" or nxt.get("size") != it.get("size"):
        return False
    t = nxt["text"].lstrip()
    if not LATIN_TOKEN_RE.match(t):
        return False
    est = len(t.split(" ")[0]) * it["size"] * 0.55
    return it["x1"] + est > RIGHT_EDGE - 2


def md_escape_lead(s):
    if not MD_LEAD_RE.match(s):
        return s
    if s[0].isdigit():
        i = s.index(".")
        return s[:i] + "\\." + s[i + 1:]
    return "\\" + s


def page_items(page):
    tabs = page.find_tables().tables
    tab_rects = [pymupdf.Rect(t.bbox) for t in tabs]
    items = [{"y": r.y0, "kind": "table", "rows": t.extract()} for t, r in zip(tabs, tab_rects)]
    ph = page.rect.height
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for ln in b["lines"]:
            spans = [s for s in ln["spans"] if s["text"]]
            text = "".join(s["text"] for s in spans)
            if not text.strip():
                continue
            x0, y0, x1, y1 = ln["bbox"]
            size = round(max(s["size"] for s in spans), 1)
            bold = any("Bold" in s["font"] for s in spans if s["text"].strip())
            it = {"size": size}
            if is_size(it, "running_head"):
                continue
            if text.strip().isdigit() and y0 > ph * 0.88:          # 폴리오
                continue
            r = pymupdf.Rect(x0, y0, x1, y1)
            if any(tr.intersects(r) for tr in tab_rects):
                continue
            kind = "bullet" if text.strip() == BULLET else "line"
            # 글머리표 글리프는 항목 본문보다 조금 아래에 앉는다 — 정렬용 y를 앞당긴다
            items.append({"y": y0 - 6 if kind == "bullet" else y0, "kind": kind, "text": text,
                          "size": size, "bold": bold, "x0": x0, "x1": x1})
    items.sort(key=lambda it: it["y"])
    return items


def cell_text(c):
    if c is None:
        return ""
    out = []
    for i, p in enumerate(str(c).split("\n")):
        if i > 0:
            prev = out[-1] if out else ""
            if prev.endswith(" ") or (prev and "가" <= prev[-1] <= "힣" and p and "가" <= p[0] <= "힣"):
                out.append(p)
            else:
                out.append(" " + p)
        else:
            out.append(p)
    return "".join(out).replace("|", "\\|").strip()


def table_md(rows):
    rows = [[cell_text(c) for c in r] for r in rows]
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * ncol]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


class Builder:
    def __init__(self):
        self.chapters, self.pending_part = [], None
        self.para, self.panel, self.list_items, self.ref_items = [], None, [], []
        self.bullet_pending, self.warnings = False, []
        self._list_open = self._ref_open = False
        self._last_body = None

    @property
    def cur(self):
        if not self.chapters:
            raise SystemExit("장 제목(chapter 급수) 전에 본문이 나왔다 — sizes.chapter 또는 skip_pages 확인")
        return self.chapters[-1]

    def flush_para(self):
        if self.para:
            self.cur["blocks"].append(md_escape_lead("".join(self.para).strip()))
            self.para = []

    def flush_panel(self):
        if self.panel is not None:
            head = "::: tip" + (f" {self.panel['title']}" if self.panel["title"] else "")
            self.cur["blocks"].append(f"{head}\n" + "\n\n".join(self.panel["paras"]) + "\n:::")
            self.panel = None

    def flush_list(self):
        if self.list_items:
            self.cur["blocks"].append("\n".join("- " + x.strip() for x in self.list_items))
            self.list_items = []

    def flush_ref(self):
        if self.ref_items:
            self.cur["blocks"].append("\n".join(x.strip() for x in self.ref_items))
            self.ref_items = []

    def flush_all(self):
        self.flush_para(); self.flush_panel(); self.flush_list(); self.flush_ref()

    def feed(self, it, pno, nxt=None):
        if it["kind"] == "table":
            self.bullet_pending = False
            self.flush_all()
            self.cur["blocks"].append(table_md(it["rows"]))
            return
        if it["kind"] == "bullet":
            self.flush_para(); self.flush_panel(); self.flush_ref()
            self.bullet_pending = True
            return
        text, bold, x1 = it["text"], it["bold"], it["x1"]
        if is_size(it, "chapter") and bold:
            self.bullet_pending = False
            self.flush_all()
            self.chapters.append({"title": text.strip(), "blocks": [], "part": self.pending_part, "page": pno})
            self.pending_part = None
            return
        if is_size(it, "part") and bold:
            self.flush_all()
            self.pending_part = text.strip()
            return
        if is_size(it, "section") and bold:
            self.bullet_pending = False
            self.flush_all()
            t = text.strip()
            if PROMPT_H2_RE.match(t):
                self.panel = {"title": t, "paras": [], "last_y": None}
            else:
                self.cur["blocks"].append("## " + t)
            return
        if is_size(it, "panel"):
            self.flush_para(); self.flush_list(); self.flush_ref()
            if self.panel is None:
                self.panel = {"title": None, "paras": [], "last_y": None}
            elif self.panel["last_y"] is not None and it["y"] - self.panel["last_y"] > PANEL_GAP:
                if self.panel["title"] is None:
                    self.flush_panel()
                    self.panel = {"title": None, "paras": [], "last_y": None}
                else:
                    self.panel["paras"].append("---")
            self.panel["paras"].append(md_escape_lead(text.strip()))
            self.panel["last_y"] = it["y"]
            return
        if self.bullet_pending:
            self.bullet_pending = False
            self.flush_para()
            self.list_items.append(text)
            self._list_open = x1 >= FULL_X1 or latin_wrap(it, nxt)
            return
        if self.list_items and self._list_open and is_size(it, "body"):
            self.list_items[-1] += text
            self._list_open = x1 >= FULL_X1 or latin_wrap(it, nxt)
            return
        if (is_size(it, "ref") and not bold) or (self.ref_items and is_size(it, "body") and REF_ITEM_RE.match(text)):
            self.flush_para(); self.flush_panel(); self.flush_list()
            if REF_ITEM_RE.match(text) and not self._ref_open:
                self.ref_items.append(text)
            elif self.ref_items:
                self.ref_items[-1] += text
            else:
                self.ref_items.append(text)
            self._ref_open = x1 >= (FULL_X1_REF if is_size(it, "ref") else FULL_X1) or latin_wrap(it, nxt)
            return
        if self.ref_items and is_size(it, "body") and self._ref_open:
            self.ref_items[-1] += text
            self._ref_open = x1 >= FULL_X1 or latin_wrap(it, nxt)
            return
        self.flush_panel(); self.flush_list(); self.flush_ref()
        if not is_size(it, "body"):
            self.warnings.append(f"p{pno}: 예상 밖 급수 {it['size']}{'B' if bold else ''}: {text[:40]!r}")
        if self.para and self._last_body and self._last_body[0] == pno and it["y"] - self._last_body[1] > PARA_GAP:
            self.flush_para()
        self._last_body = (pno, it["y"])
        self.para.append(text)
        if x1 < FULL_X1 and not latin_wrap(it, nxt):
            self.flush_para()


def build():
    doc = pymupdf.open(str(SRC))
    b = Builder()
    for pno in range(1, doc.page_count + 1):
        if pno in SKIP_PAGES:
            continue
        items = page_items(doc[pno - 1])
        for i, it in enumerate(items):
            b.feed(it, pno, items[i + 1] if i + 1 < len(items) else None)
    b.flush_all()
    return b


def gift_md():
    if not GIFT:
        return ""
    lines = "\n\n".join(GIFT.get("lines", []))
    url = GIFT.get("url")
    link = f"\n\n[{url}]({url})" if url else ""
    return f"::: warn {GIFT.get('title', '')}\n{lines}{link}\n:::\n"


def write_book(b):
    chap_dir = BOOK / "chapters"
    chap_dir.mkdir(parents=True, exist_ok=True)
    for old in chap_dir.glob("ch-*.md"):
        old.unlink()
    author = [c for c in b.chapters if c["title"] == AUTHOR_TITLE]
    others = [c for c in b.chapters if c["title"] != AUTHOR_TITLE]
    author_md = ""
    if author:
        blocks = list(author[0]["blocks"])
        name = blocks[0][3:] if blocks and blocks[0].startswith("## ") else ""
        body = blocks[1:] if name else blocks
        for anchor, extra in AUTHOR_ADDITIONS:
            if anchor in body:
                body.insert(body.index(anchor) + 1, extra)
            else:
                body.append(extra)
        head = f"**{name}**\n\n" if name else ""
        author_md = f"::: quote {AUTHOR_TITLE}\n{head}" + "\n\n".join(body) + "\n:::\n\n::: lead\n:::\n\n"
    part_no, files = 0, []
    for i, ch in enumerate(others):
        parts = []
        if ch["part"]:
            m = PART_RE.match(ch["part"])
            part_no = int(m.group(1)) if m else part_no + 1
            parts.append(f"::: info PART {part_no:02d}\n{ch['part']}\n:::")
        parts.append("# " + ch["title"])
        parts.extend(ch["blocks"])
        text = "\n\n".join(parts) + "\n"
        files.append((ch["title"], (author_md + text) if i == 0 else text))
    g = gift_md()
    if g:
        t, txt = files[-1]
        files[-1] = (t, txt.rstrip("\n") + "\n\n::: lead\n:::\n\n" + g)
    hits = {d["text"]: 0 for d in DELETIONS}
    outline = []
    for i, (title, text) in enumerate(files):
        for d in DELETIONS:
            n = text.count(d["text"])
            if n:
                hits[d["text"]] += n
                text = text.replace(d["text"], "")
        text = re.sub(r"\n{3,}", "\n\n", text)
        fn = f"ch-{i:02d}.md"
        (chap_dir / fn).write_text(text, encoding="utf-8")
        outline.append({"file": fn, "title": title})
    missing = [t for t, n in hits.items() if n == 0]
    if missing:
        raise SystemExit("삭제 문구 미일치(원문 그대로 복사했는지 확인): " + " | ".join(m[:40] for m in missing))
    (BOOK / "outline.json").write_text(json.dumps({"chapters": outline}, ensure_ascii=False, indent=2), encoding="utf-8")
    return outline


def norm(s):
    return re.sub(r"\s+", "", s)


def verify(b):
    doc = pymupdf.open(str(SRC))
    src = []
    for pno in range(1, doc.page_count + 1):
        if pno in SKIP_PAGES:
            continue
        for it in page_items(doc[pno - 1]):
            if it["kind"] == "table":
                src += ["".join(cell_text(c).replace("\\|", "|") for c in r) for r in it["rows"]]
            elif it["kind"] == "line":
                src.append(it["text"])
    src_n = norm("".join(src))
    for d in DELETIONS:
        t = d["text"][3:] if d["text"].startswith("## ") else d["text"]
        src_n = src_n.replace(norm(t), "")
    by_title = {}
    for f in sorted((BOOK / "chapters").glob("ch-*.md")):
        text = f.read_text(encoding="utf-8")
        title = next((l[2:].strip() for l in text.split("\n") if l.startswith("# ")), f.name)
        if text.startswith(f"::: quote {AUTHOR_TITLE}"):
            head, _, rest = text.partition("\n# ")
            for _, extra in AUTHOR_ADDITIONS:
                head = head.replace("\n\n" + extra, "")
            by_title[AUTHOR_TITLE] = head.replace("::: quote ", "::: tip ").replace("**", "")
            text = "# " + rest
        by_title[title] = text
    out = []
    for ch in b.chapters:
        for line in by_title[ch["title"]].split("::: warn ")[0].split("\n"):
            s = line
            if s.startswith("::: info") or s.strip() == "::: quote":
                continue
            if s.startswith("::: tip"):
                s = s[len("::: tip"):]
            if s.strip() in (":::", "---", "::: lead") or re.match(r"^\|(---\|)+$", s.strip()):
                continue
            for pre in ("# ", "## ", "- "):
                if s.startswith(pre):
                    s = s[len(pre):]
                    break
            s = s.replace("\\|", "|").replace("\\.", ".").replace("\\", "")
            if s.startswith("| ") and s.endswith(" |"):
                s = s[2:-2].replace(" | ", "")
            out.append(s)
    md_n = norm("".join(out))
    if src_n == md_n:
        return True, f"원문 ↔ md 문자열 일치(공백·표기 기호 제외) — {len(src_n):,}자"
    i = 0
    while i < min(len(src_n), len(md_n)) and src_n[i] == md_n[i]:
        i += 1
    return False, (f"불일치: 원문 {len(src_n):,}자 vs md {len(md_n):,}자, 첫 차이 {i}\n"
                   f"  원문: …{src_n[max(0, i - 30):i]}⟦{src_n[i:i + 40]}⟧\n"
                   f"  md  : …{md_n[max(0, i - 30):i]}⟦{md_n[i:i + 40]}⟧")


if __name__ == "__main__":
    b = build()
    outline = write_book(b)
    ok, msg = verify(b)
    print(f"장 {len(outline)}개" + (" (+특별 선물)" if GIFT else ""))
    for w in b.warnings[:30]:
        print("WARN", w)
    print(("OK " if ok else "FAIL ") + msg)
    sys.exit(0 if ok else 2)
