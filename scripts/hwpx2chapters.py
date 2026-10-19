#!/usr/bin/env python3
"""HWPX 원고 -> bookforge 책 프로젝트(chapters/*.md + outline.json + assets/fig-NN.png), 원문 무수정 검증 내장.

한글(HWPX) 원고는 스타일 이름이 대개 "바탕글" 하나라, 역할을 **글자 크기·굵기·왼쪽 여백**으로 판정한다.
원문 문장은 바꾸지 않는다. 바꾸는 것은 구조 표지뿐이다.

  역할(book.json manuscript.hwpx 로 지정, 없으면 --profile 결과로 채운다)
    chapter   (pt, 굵게)  -> "# 장 제목" 새 장 파일
    section   (pt, 굵게)  -> "##"
    subsection(pt, 굵게)  -> "###"
    indents.quote   왼쪽 여백(HWPUNIT) -> "> 인용"(연속 문단 묶음)
    indents.code    왼쪽 여백 -> ``` 코드 블록(빈 줄 포함 연속 묶음)
    indents.bullet  왼쪽 여백 + 글머리 글자(bullet_glyph, 기본 "· ") -> "- 목록"
    그림 문단 + 바로 다음 캡션 문단(caption_regex) -> ![캡션](../assets/fig-NN.png)
    표 -> GFM 표(첫 행 = 머리 행). transpose_min_cols 열 이상이면 행·열을 바꿔 싣는다(글자 불변)
    굵은 런 -> **…**,  link_color 색의 URL 한 줄 -> [url](url)
    author_title(기본 "지은이") 장 -> 앞부속 저자 소개 카드(::: quote)
  범위
    body_start_text: 이 글자로 된 장 크기 문단부터 본문(앞의 표지·수동 차례는 버림). 없으면
                     "차례" 계열 스타일 문단 다음의 첫 장 크기 문단.
    캡션 없는 끝 그림(출판사 로고 등)은 버린다(경고 출력).
  선택
    korean_outline: true 면 절·소제목의 십진 번호(1.1 / 2.3.1)를 한국식(1. / 1))으로 — 원고 글자 변경이므로 사용자 요청·승인 시에만.
    author_additions: [{"after": 0, "text": "…"}] 저자 카드에 원고 밖 약력 추가(0 = 이름 다음). 대조에서 제외.
    edits: [{"id": "교정 7", "old": "md 원문(정확히 1회)", "new": "…", "why": "…"}] 승인된 교정. 대조는 "원고+수정=md",
           적용 내역은 qc/edits_applied.txt. 재변환해도 유지된다.
    fig_renumber: true 면 캡션 "그림 N." 을 등장 순서로 다시 매긴다 — **원고 글자 변경이므로 사용자 승인 후에만**.

사용
  python hwpx2chapters.py <책폴더> --profile     # 원고 실측 -> qc/hwpx_profile.txt (역할 설정용)
  python hwpx2chapters.py <책폴더>               # 변환 + 원문 대조
원고 경로는 book.json manuscript.source (책폴더 기준 상대경로).
"""
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree
from markdown_it import MarkdownIt

DEFAULTS = {
    "body_start_text": None,
    "chapter": 16.0, "section": 12.0, "subsection": 10.5,
    "indents": {"quote": "1134", "code": "567", "bullet": "425"},
    "bullet_glyph": "· ",
    "caption_regex": r"^그림 (\d+)\.\s",
    "fig_renumber": False,
    "transpose_min_cols": 9,
    "author_title": "지은이",
    "link_color": "#0000FF",
    "korean_outline": False,
    "author_additions": [],
    "edits": [],
}


ZWSP_ENTITY = "&#8203;"      # 굵게 닫힘 보조(폭 없는 공백) — 원문 대조에서는 지운다


def local(tag):
    return tag.rsplit("}", 1)[-1]


def t_text(t):
    """<hp:t> 안의 <hp:tab/>·<hp:lineBreak/> 꼬리까지 포함한 글자(t.text 만 읽으면 탭 뒤 글자가 사라진다)."""
    out = [t.text or ""]
    for ch in t:
        if local(ch.tag) in ("tab", "lineBreak"):
            out.append(" ")
        out.append(ch.tail or "")
    return "".join(out)


def korean_outline(head):
    """십진 개요번호 -> 한국식(두온 POD 원고서식: 개요2 "1." / 개요3 "1)").
    "1.1  제목" -> "1. 제목",  "2.3.1  제목" -> "1) 제목". 장 번호("N장")는 그대로."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)\.?\s+", head)
    if m:
        return f"{m.group(3)}) " + head[m.end():]
    m = re.match(r"^(\d+)\.(\d+)\.?\s+", head)
    if m:
        return f"{m.group(2)}. " + head[m.end():]
    return head


def md_escape(text):
    text = re.sub(r"([\\`*_<>\[\]#|])", r"\\\1", text)
    text = re.sub(r"^(\d+)\.(\s)", r"\1\\.\2", text)
    text = re.sub(r"^([-+])(\s)", r"\\\1\2", text)
    return text


class Doc:
    def __init__(self, hwpx):
        z = zipfile.ZipFile(hwpx)
        self.zip = z
        head = etree.fromstring(z.read("Contents/header.xml"))
        self.cpr = {c.get("id"): (int(c.get("height")) / 100, c.find("{*}bold") is not None, c.get("textColor"))
                    for c in head.iter("{*}charPr")}
        self.ppr = {}
        for p in head.iter("{*}paraPr"):
            m = p.find(".//{*}margin/{*}left")
            self.ppr[p.get("id")] = m.get("value") if m is not None else "0"
        self.styles = {s.get("id"): s.get("name") for s in head.iter("{*}style")}
        secs = sorted((n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n)),
                      key=lambda n: int(re.search(r"\d+", n).group()))
        self.paras = []
        for n in secs:
            self.paras += [p for p in etree.fromstring(z.read(n)) if local(p.tag) == "p"]

    def runs(self, p):
        """문단 직속 런: [(size, bold, color, text)] — 표·그림 안 글자는 제외."""
        out = []
        for r in p.findall("{*}run"):
            size, bold, color = self.cpr.get(r.get("charPrIDRef"), (10.0, False, "#000000"))
            txt = "".join(t_text(t) for t in r.findall("{*}t"))
            if txt:
                out.append((size, bold, color, txt))
        return out

    def indent(self, p):
        return self.ppr.get(p.get("paraPrIDRef"), "0")

    def style(self, p):
        return self.styles.get(p.get("styleIDRef"), "")

    def cell_text(self, tc):
        paras = ["".join(t_text(t) for t in sp.iter("{*}t")).strip() for sp in tc.iter("{*}p")]
        paras = [x for x in paras if x]
        if len(paras) > 1:
            sys.exit(f"표 칸에 문단이 여럿 — GFM 칸은 줄바꿈을 못 담는다: {paras!r}")
        return paras[0] if paras else ""


def para_info(doc, p):
    runs = doc.runs(p)
    text = "".join(r[3] for r in runs).strip()
    size = next((r[0] for r in runs if r[3].strip()), None)
    allbold = bool(text) and all(r[1] for r in runs if r[3].strip())
    return runs, text, size, allbold


def find_body_start(doc, cfg):
    """본문 첫 문단(1-based). 앞의 표지 블록·수동 차례를 건너뛴다."""
    want = cfg["body_start_text"]
    last_toc = 0
    for i, p in enumerate(doc.paras, 1):
        if "차례" in doc.style(p):
            last_toc = i
    for i, p in enumerate(doc.paras, 1):
        if i <= last_toc:
            continue
        _, text, size, allbold = para_info(doc, p)
        if size == cfg["chapter"] and allbold and (want is None or re.sub(r"\s+", " ", text) == want):
            return i
    sys.exit("본문 시작 문단을 못 찾음 — book.json manuscript.hwpx.body_start_text 를 지정")


def profile(doc, book):
    out = [f"문단 {len(doc.paras)}개 · 섹션 합산", ""]
    toc = [i for i, p in enumerate(doc.paras, 1) if "차례" in doc.style(p)]
    if toc:
        out.append(f"차례 스타일 문단: {toc[0]}~{toc[-1]} (본문 자동 시작은 그 뒤 첫 장 크기 문단)")
    stats, ex = Counter(), {}
    for i, p in enumerate(doc.paras, 1):
        runs, text, size, allbold = para_info(doc, p)
        tbl, pic = p.find(".//{*}tbl") is not None, p.find(".//{*}pic") is not None
        kind = "표" if tbl else "그림" if pic else ""
        k = (size, "굵게" if allbold else "", doc.indent(p), kind)
        stats[k] += 1
        ex.setdefault(k, []).append(f"{i}:{text[:40]}")
    out.append("\n(글자 크기, 전체 굵게, 왼쪽 여백, 표/그림) 개수 — 예시")
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        out.append(f"{v:5d}  {k}  " + " | ".join(ex[k][:3]))
    ncols = Counter()
    for p in doc.paras:
        for t in p.iter("{*}tbl"):
            ncols[int(t.get("colCnt"))] += 1
            for sp in t.iter("{*}cellSpan"):
                if sp.get("colSpan") != "1" or sp.get("rowSpan") != "1":
                    out.append("⚠ 병합 셀이 있는 표 — 변환 규칙 없음(원고 확인 필요)")
                    break
    out.append(f"\n표 열 수 분포: {dict(sorted(ncols.items()))}")
    dst = book / "qc" / "hwpx_profile.txt"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"OK {dst}")


def table_rows(doc, tbl):
    rows = []
    for tr in tbl.findall("{*}tr"):
        row = []
        for tc in tr.findall("{*}tc"):
            sp = tc.find("{*}cellSpan")
            if sp.get("colSpan") != "1" or sp.get("rowSpan") != "1":
                sys.exit("병합 셀이 있는 표 — 변환 규칙 없음")
            row.append(doc.cell_text(tc))
        rows.append(row)
    return rows


def md_table(rows):
    lines = ["| " + " | ".join(md_escape(c) for c in rows[0]) + " |", "|" + "---|" * len(rows[0])]
    lines += ["| " + " | ".join(md_escape(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def transpose(rows):
    """칸 이름이 머리 행인 기록표 -> 칸 이름이 행이 되는 표(첫 열 값이 새 머리 행)."""
    head = [rows[0][0]] + [r[0] for r in rows[1:]]
    return [head] + [[rows[0][j]] + [r[j] for r in rows[1:]] for j in range(1, len(rows[0]))]


def inline_md(runs):
    """굵은 런 -> **…**. 앞뒤 공백은 굵게 밖으로, 인접 굵은 런은 병합."""
    parts, bold_n = [], 0
    for _, bold, _, txt in runs:
        if bold and txt.strip():
            lead, trail = txt[: len(txt) - len(txt.lstrip())], txt[len(txt.rstrip()):]
            parts.append(f"{lead}**{md_escape(txt.strip())}**{trail}")
            bold_n += 1
        else:
            parts.append(md_escape(txt))
    s = "".join(parts)
    merged = s.count("****")
    s = s.replace("****", "")

    # 굵은 부분이 문장부호로 끝나고 바로 글자가 이어지면(**「해당 없음」**으로) CommonMark 가 닫지 못한다
    # -> 닫는 ** 뒤에 폭 없는 공백 엔티티(&#8203;)를 둔다. "&" 가 ASCII 문장부호라 닫힘 조건을 채우고,
    #    화면에는 아무것도 안 보인다. 닫는 부호까지 원문대로 굵게 유지(예전: 부호를 굵게 밖으로 빼서 굵기가 달라졌다).
    def fix(m):
        return f"**{m.group(1)}**{ZWSP_ENTITY}"
    s = re.sub(r"\*\*((?:[^*]|\\\*)+?)\*\*(?=(\S))",
               lambda m: fix(m) if unicodedata.category(m.group(1)[-1]).startswith("P")
               and not unicodedata.category(m.group(2)).startswith("P") else m.group(0), s)
    return s, bold_n - merged


def convert(doc, book, cfg):
    ind = cfg["indents"]
    cap_re = re.compile(cfg["caption_regex"])
    glyph = cfg["bullet_glyph"]
    (book / "chapters").mkdir(parents=True, exist_ok=True)
    (book / "assets").mkdir(parents=True, exist_ok=True)

    chapters, cur, author = [], None, None
    source_text, fig_no, renumbered, dropped = [], 0, [], []
    outline_changes = []
    unknown = Counter()
    buf_kind, buf = None, []

    def target():
        return author["blocks"] if author is not None and cur is None else cur["blocks"]

    def flush():
        nonlocal buf_kind, buf
        if buf:
            if buf_kind == "quote":
                block = "\n>\n".join("> " + x for x in buf)
            elif buf_kind == "code":
                while buf and not buf[-1].strip():
                    buf.pop()
                block = "```\n" + "\n".join(buf) + "\n```"
            else:
                block = "\n".join("- " + x for x in buf)
            target().append(block)
        buf_kind, buf = None, []

    def push(kind, line):
        nonlocal buf_kind
        if buf_kind != kind:
            flush()
            buf_kind = kind
        buf.append(line)

    start = find_body_start(doc, cfg)
    i = start
    n = len(doc.paras)
    body_sizes = Counter()
    while i <= n:
        p = doc.paras[i - 1]
        runs, text, size, allbold = para_info(doc, p)
        tbl, pic = p.find(".//{*}tbl"), p.find(".//{*}pic")
        pind = doc.indent(p)

        if tbl is not None or pic is not None:
            flush()
            if text:
                sys.exit(f"문단 {i}: 표·그림 문단에 글자가 함께 있음 {text!r}")
            if tbl is not None:
                rows = table_rows(doc, tbl)
                if len(rows[0]) >= cfg["transpose_min_cols"]:
                    rows = transpose(rows)            # 대조 원문도 전치 순서로
                for r in rows:
                    source_text.extend(r)
                target().append(md_table(rows))
                i += 1
                continue
            cap = para_info(doc, doc.paras[i])[1] if i < n else ""
            m = cap_re.match(cap)
            if not m:
                dropped.append(f"문단 {i}: 캡션 없는 그림(로고 등) 버림 — 다음 문단 {cap[:30]!r}")
                i += 1
                continue
            fig_no += 1
            bid = pic.find(".//{*}img").get("binaryItemIDRef")
            name = next(x for x in doc.zip.namelist() if x.startswith(f"BinData/{bid}."))
            fn = f"fig-{fig_no:02d}{Path(name).suffix.lower()}"
            (book / "assets" / fn).write_bytes(doc.zip.read(name))
            if cfg["fig_renumber"] and m.groups() and int(m.group(1)) != fig_no:
                renumbered.append((m.group(1), fig_no, cap))
                cap = cap[:m.start(1)] + str(fig_no) + cap[m.end(1):]
            source_text.append(cap)
            target().append(f"![{md_escape(cap)}](../assets/{fn})")
            i += 2
            continue

        if not text:
            if buf_kind == "code" and pind == ind["code"]:
                buf.append("")
            i += 1
            continue

        source_text.append(text)
        if size == cfg["chapter"] and allbold:
            flush()
            title = re.sub(r"\s+", " ", text)
            if title == cfg["author_title"]:
                source_text.pop()                       # 표제는 카드가 "저자 소개"로 그린다
                author = {"blocks": [], "src_from": len(source_text)}
                cur = None
                i += 1
                continue
            if author is not None and "src_to" not in author:
                author["src_to"] = len(source_text) - 1
            cur = {"title": title, "blocks": []}
            chapters.append(cur)
        elif size in (cfg["section"], cfg["subsection"]) and allbold:
            flush()
            head = re.sub(r"\s+", " ", text)
            if cfg["korean_outline"]:
                new = korean_outline(head)
                if new != head:
                    outline_changes.append((head, new))
                    source_text[-1] = new               # 승인된 번호 변경 — 대조 원문도 바뀐 번호로
                    head = new
            target().append(("## " if size == cfg["section"] else "### ") + md_escape(head))
        elif pind == ind.get("quote"):
            push("quote", inline_md(runs)[0].strip())
        elif pind == ind.get("code"):
            push("code", text)
        elif pind == ind.get("bullet") and text.startswith(glyph.strip()):
            rr = list(runs)
            f = rr[0]
            rr[0] = (f[0], f[1], f[2], f[3].lstrip()[len(glyph.strip()):].lstrip())
            source_text[-1] = text[len(glyph.strip()):].lstrip()     # 글머리는 목록 표지로 바뀜
            push("list", inline_md(rr)[0].strip())
        else:
            flush()
            body_sizes[size] += 1
            if any(r[2] == cfg["link_color"] for r in runs) and re.fullmatch(r"https?://\S+", text):
                target().append(f"[{md_escape(text)}]({text})")
            else:
                target().append(inline_md(runs)[0].strip())
            if allbold and size:
                unknown[size] += 1
        i += 1
    flush()
    if author is not None:
        a0, a1 = author["src_from"], author.get("src_to", len(source_text))
        source_text = source_text[a0:a1] + source_text[:a0] + source_text[a1:]

    # ---- 쓰기 ----
    outline = []
    for k, ch in enumerate(chapters):
        parts = []
        if k == 0 and author is not None:
            card = [re.sub(r"^> ?", "", b) for b in author["blocks"] if b.strip() != ">"]
            # 저자가 원고 밖에서 준 약력 추가분 — {"after": 카드 문단 번호(0 = 이름), "text": "…"}
            for add in sorted(cfg["author_additions"], key=lambda a: -a["after"]):
                card.insert(add["after"] + 1, md_escape(add["text"]))
            parts.append("::: quote 저자 소개\n" + "\n\n".join(card) + "\n\n:::")
            parts.append("::: lead\n:::")
        parts.append("# " + ch["title"])
        parts.extend(ch["blocks"])
        fn = f"ch-{k:02d}.md"
        (book / "chapters" / fn).write_text("\n\n".join(parts) + "\n", encoding="utf-8")
        outline.append({"file": fn, "title": ch["title"]})
    (book / "outline.json").write_text(json.dumps({"chapters": outline}, ensure_ascii=False, indent=2),
                                       encoding="utf-8")

    # ---- 승인된 원고 수정(edits) — 저자·편집자가 승인한 교정만. old 는 전체 원고에서 정확히 한 번 나와야 한다 ----
    plain = lambda x: re.sub(r"\\(.)", r"\1", x.replace("**", "").replace(ZWSP_ENTITY, ""))
    texts = {o["file"]: (book / "chapters" / o["file"]).read_text(encoding="utf-8") for o in outline}
    edit_log = []
    for e in cfg["edits"]:
        cnt = sum(t.count(e["old"]) for t in texts.values())
        if cnt != 1:
            sys.exit(f"FAIL 수정 문구가 원고에 {cnt}번 나옴(정확히 1번이어야 함): {e['old'][:50]!r}")
        f = next(k for k, t in texts.items() if e["old"] in t)
        texts[f] = texts[f].replace(e["old"], e["new"])
        edit_log.append(f"[{e.get('id', '')}] {f}\n  원문: {plain(e['old'])}\n  수정: {plain(e['new'])}\n  사유: {e.get('why', '')}")
    for f, t in texts.items():
        (book / "chapters" / f).write_text(t, encoding="utf-8")
    if edit_log:
        (book / "qc" / "edits_applied.txt").write_text("\n\n".join(edit_log) + "\n", encoding="utf-8")

    # ---- 원문 대조(공백 무시, 순서까지): 원고 + 승인 수정 = 현재 md ----
    md_all = "\n".join((book / "chapters" / o["file"]).read_text(encoding="utf-8") for o in outline)
    md_all = re.sub(r"^::: (quote|lead)( .*)?$|^:::$", "", md_all, flags=re.M)
    if author is not None:
        md_all = md_all.replace("저자 소개", "", 1)
        for add in cfg["author_additions"]:                  # 승인된 추가분은 원문 대조에서 뺀다
            md_all = md_all.replace(md_escape(add["text"]), "", 1)
    for pat, rep in ((r"^#+ ", ""), (r"^```$", ""), (r"^> ?", ""), (r"^- ", ""), (r"^\|(-{3}\|)+$", ""),
                     (r"!\[(.*)\]\(\.\./assets/fig-\d+\.\w+\)", r"\1"), (r"\[(https?://[^\]]+)\]\(\S+\)", r"\1")):
        md_all = re.sub(pat, rep, md_all, flags=re.M)
    md_all = md_all.replace("**", "").replace(ZWSP_ENTITY, "")
    md_all = re.sub(r"(?<!\\)\|", "", md_all)
    md_all = re.sub(r"\\(.)", r"\1", md_all)
    norm = lambda s: re.sub(r"\s", "", s)
    a, b = norm("".join(source_text)), norm(md_all)
    for e in cfg["edits"]:                                   # 원고 쪽에도 같은 승인 수정을 적용해 대조
        o_, n_ = norm(plain(e["old"])), norm(plain(e["new"]))
        if a.count(o_) != 1:
            sys.exit(f"FAIL 수정 원문이 HWPX 원고에 {a.count(o_)}번 나옴: {plain(e['old'])[:50]!r}")
        a = a.replace(o_, n_)
    for d in dropped:
        print("WARN " + d)
    body_size = max(body_sizes, key=body_sizes.get, default=0)
    for s, c in unknown.items():
        if s <= body_size:
            continue                                   # 본문 크기 굵은 문단 = 강조 문장(정상)
        print(f"WARN 역할 미배정 굵은 {s}pt 문단 {c}개 — 제목이면 book.json manuscript.hwpx 에 크기 지정")
    if a != b:
        k = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]), min(len(a), len(b)))
        sys.exit(f"FAIL 원문 ↔ md 불일치 @{k}: 원문 {a[k-30:k+30]!r} / md {b[k-30:k+30]!r}")
    md = MarkdownIt("commonmark").enable("table")
    strong = sum(1 for o in outline for t in md.parse((book / "chapters" / o["file"]).read_text(encoding="utf-8"))
                 if t.type == "inline" for c in (t.children or []) if c.type == "strong_open")
    pairs = sum((book / "chapters" / o["file"]).read_text(encoding="utf-8").count("**") for o in outline) // 2
    if strong != pairs:
        print(f"WARN 굵게 표시 {pairs}쌍 중 {pairs - strong}쌍이 강조로 파싱 안 됨 — 해당 문장 확인")
    if outline_changes:
        print(f"개요번호 한국식 변경 {len(outline_changes)}건 — 예: {outline_changes[0][0]!r} -> {outline_changes[0][1]!r}")
        (book / "qc" / "outline_numbering.txt").write_text(
            "\n".join(f"{a}\t->\t{b}" for a, b in outline_changes) + "\n", encoding="utf-8")
    for old, new, cap in renumbered:
        print(f"그림 번호 {old} -> {new}: {cap[:40]}")
    print(f"OK 원문 ↔ md 일치 — 본문 시작 문단 {start}, 장 {len(outline)}개, 그림 {fig_no}개, "
          f"저자 카드 {'있음' if author else '없음'}, {len(a):,}자")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    book = Path(sys.argv[1])
    conf = json.loads((book / "book.json").read_text(encoding="utf-8"))
    ms = conf.get("manuscript", {})
    src = (book / ms["source"]).resolve()
    cfg = {**DEFAULTS, **ms.get("hwpx", {})}
    cfg["indents"] = {**DEFAULTS["indents"], **ms.get("hwpx", {}).get("indents", {})}
    doc = Doc(src)
    if "--profile" in sys.argv:
        profile(doc, book)
    else:
        convert(doc, book, cfg)


if __name__ == "__main__":
    main()
