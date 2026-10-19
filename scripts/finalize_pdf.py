#!/usr/bin/env python3
"""QC 를 통과한 final PDF 에 출판용 마무리를 입힌다(본문·조판은 건드리지 않음).

- 북마크 3단: 표지·차례·저자 소개 / 부(간지) → 장 → 절 / 에필로그·부록 등 / 특별 선물·판권
- 문서 정보: 제목·저자·주제·키워드(ISBN 포함)·만든 곳, 언어 ko-KR
- 열람 모드: 북마크 창 표시(UseOutlines)

사용: python3 finalize_pdf.py <book_dir> <출력.pdf>
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

BOOK = Path(sys.argv[1])
OUT = Path(sys.argv[2])
SRC = BOOK / "final" / f"{BOOK.name}.pdf"
CH_NUM_RE = re.compile(r"^제?\d+장\s")


def norm(s):
    return re.sub(r"\s+", "", s)


def parts_from_md():
    """chapters/*.md 의 '::: info PART NN' 블록 → [(label, title, 다음 장 제목)]"""
    out = []
    for f in sorted((BOOK / "chapters").glob("ch-*.md")):
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^::: info (PART \d+)\n(.+?)\n:::", text, re.M)
        if m:
            first = re.search(r"^# (.+)$", text, re.M).group(1).strip()
            out.append((m.group(1), m.group(2).strip(), first))
    return out


def main():
    book = json.loads((BOOK / "book.json").read_text(encoding="utf-8"))
    col = book.get("colophon", {})
    doc = pymupdf.open(SRC)
    n = doc.page_count
    old = doc.get_toc(simple=True)          # [lvl, title, page] — 장(1)·절(2)

    # 자간을 준 라벨(C O N T E N T S 등)이 띄어져 추출되므로 공백을 지운 텍스트로 비교한다
    texts = [norm(doc[i].get_text()) for i in range(n)]

    def find_page(pred, start=1):
        for i in range(start - 1, n):
            if pred(texts[i]):
                return i + 1
        return None

    toc_p = find_page(lambda t: "CONTENTS" in t and "차례" in t)
    author_p = find_page(lambda t: "PROFILE" in t and "저자소개" in t)
    gift_p = find_page(lambda t: "GIFT" in t and "특별선물" in t)
    colo_p = find_page(lambda t: "ISBN" in t and "펴낸곳" in t, start=n - 2)

    parts = parts_from_md()
    part_at = {}                             # 장 제목 → (부 제목, 간지 면)
    first_body = (author_p or toc_p or 1) + 1   # 간지는 차례·앞부속 뒤에서만 찾는다(차례에도 부 제목이 있다)
    for label, title, first in parts:
        key = norm(title)[:12]
        pg = find_page(lambda t, k=key, lb=norm(label): k in t and lb in t and len(t) < 120, start=first_body)
        part_at[first] = (title, pg)

    toc = [[1, "표지", 1]]
    if toc_p:
        toc.append([1, "차례", toc_p])
    if author_p:
        toc.append([1, "저자 소개", author_p])
    in_part = False
    for lvl, title, page in old:
        if lvl == 1:
            if title in part_at:
                ptitle, ppage = part_at[title]
                toc.append([1, ptitle, ppage or page])
                in_part = True
            elif not CH_NUM_RE.match(title):
                in_part = False              # 에필로그·부록·용어·참고자료는 부 밖
            toc.append([2 if in_part else 1, title, page])
        else:
            toc.append([lvl + (1 if in_part else 0), title, page])   # 절(2)·소제목(3) 단계 유지
    if gift_p:
        toc.append([1, book.get("gift_head", "전자책 구매자 특별 선물"), gift_p])
    if colo_p:
        toc.append([1, "판권", colo_p])
    doc.set_toc(toc)

    isbn = col.get("isbn", "")
    doc.set_metadata({
        "title": book["title"],
        "author": book.get("author", ""),
        "subject": f"{book.get('subtitle', '')} | {col.get('publisher_full', book.get('publisher', ''))} | ISBN {isbn}",
        "keywords": ", ".join(book.get("keywords", []) + [f"ISBN {isbn}"]),   # book.json keywords
        "creator": col.get("publisher_full", book.get("publisher", "")),
        "producer": "Typst · bookforge practical-a5",
    })
    cat = doc.pdf_catalog()
    doc.xref_set_key(cat, "Lang", "(ko-KR)")
    doc.set_pagemode("UseOutlines")
    doc.save(OUT, garbage=3, deflate=True)
    print(f"OK {OUT.name}: {n}쪽, 북마크 {len(toc)}개(1단 {sum(1 for t in toc if t[0]==1)}), 부 {len(parts)}개")


if __name__ == "__main__":
    main()
