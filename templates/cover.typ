// 두온교육 A5 타이포 표지 틀 — 원본 표지 이미지가 없을 때 쓴다(크레딧 없이 Typst 로 렌더).
// 책 폴더의 tools/ 에 복사한 뒤:
//   typst compile --root . --font-path ~/bookforge/assets/fonts --ignore-system-fonts --ppi 300 tools/cover.typ assets/cover.png
// 글자는 전부 book.json 에서 읽는다. book.json "cover" 예:
//   "cover": { "label": "GEO MARKETING · FIELD GUIDE",
//              "title_lines": ["AI는 우리 브랜드를", "어떻게 |말하는가"],   // "|" 뒤는 금색 강조
//              "tagline": "묻고 · 기록하고 · 고치고 · 다시 잰다",
//              "question": "30명 규모 회사에 맞는 전자결재 시스템 추천해 줘",   // 없으면 말풍선 생략
//              "highlight": "우리 브랜드는 여기에 있는가?" }
// label·tagline·question·highlight 는 원고에 없는 표지 카피다 — 사용자 확인을 받고 쓴다.
#let book = json("../book.json")
#let cv = book.at("cover", default: (:))
#let navy = rgb(book.at("cover_bg", default: "#0e2240"))
#let navy2 = navy.lighten(12%)
#let gold = rgb("#e8c874")
#let mist = rgb("#9fb3cc")
#set page(width: 148mm, height: 210mm, margin: 0mm, fill: navy)
#set text(font: "KoPubWorldDotum", lang: "ko")
#set par(justify: false, leading: 0.5em, spacing: 0pt)

// 배경 동심원(질문이 퍼져 나가는 모양)
#place(top + left, dx: 98mm, dy: 58mm, {
  for (i, r) in (14, 26, 38, 50, 62, 74).enumerate() {
    place(center + horizon, circle(radius: r * 1mm, stroke: 0.5pt + white.transparentize(82% + i * 2.5%)))
  }
})

#if "label" in cv {
  place(top + left, dx: 16mm, dy: 20mm, text(size: 7.5pt, weight: "bold", tracking: 0.32em, fill: gold, cv.label))
  place(top + left, dx: 16mm, dy: 26mm, rect(width: 10mm, height: 1.2pt, fill: gold))
}

// 질문 → AI 답 말풍선(답 안 한 줄을 금색으로 강조)
#let bubble(w, body, fill: white, stroke: none) = box(width: w, fill: fill, stroke: stroke,
  radius: 3mm, inset: (x: 4mm, y: 3.2mm), body)
#if "question" in cv {
  place(top + left, dx: 52mm, dy: 38mm, bubble(80mm, fill: white.transparentize(6%),
    text(size: 8.6pt, weight: "medium", fill: navy, cv.question)))
  place(top + left, dx: 16mm, dy: 56mm, bubble(92mm, fill: navy2, stroke: 0.6pt + white.transparentize(70%), {
    text(size: 6.8pt, weight: "bold", tracking: 0.2em, fill: mist, "AI ANSWER")
    v(2.6mm)
    for (w, hl) in ((72mm, false), (64mm, false), (70mm, true), (46mm, false)) {
      if hl and "highlight" in cv {
        box(width: w, height: 3.4mm, radius: 1mm, fill: gold.transparentize(8%),
          align(left + horizon, pad(left: 2mm, text(size: 6.8pt, weight: "bold", fill: navy, cv.highlight))))
      } else {
        box(width: w, height: 1.7mm, radius: 0.85mm, fill: white.transparentize(72%))
      }
      v(2.4mm)
    }
  }))
}

// 제목("|" 뒤는 금색)
#let lines = cv.at("title_lines", default: (book.title,))
#place(top + left, dx: 16mm, dy: 104mm, block(width: 118mm, {
  for (k, ln) in lines.enumerate() {
    if k > 0 { v(5.5mm) }
    let seg = ln.split("|")
    text(size: 27pt, weight: "bold", fill: white, tracking: -0.035em, seg.at(0))
    if seg.len() > 1 { text(size: 27pt, weight: "bold", fill: gold, tracking: -0.035em, seg.at(1)) }
  }
}))
#place(top + left, dx: 16mm, dy: 133mm, rect(width: 118mm, height: 0.6pt, fill: white.transparentize(65%)))
#place(top + left, dx: 16mm, dy: 138mm,
  text(size: 10.5pt, weight: "medium", fill: white.transparentize(10%), book.at("subtitle", default: "")))
#if "tagline" in cv {
  place(top + left, dx: 16mm, dy: 147mm, block(width: 118mm, text(size: 7.8pt, fill: mist, cv.tagline)))
}
#place(top + left, dx: 16mm, dy: 168mm,
  text(size: 11pt, weight: "bold", fill: white, [#book.author #text(weight: "medium", size: 9.5pt, fill: mist)[지음]]))
#place(bottom + left, dx: 16mm, dy: -14mm,
  box(fill: white, radius: 5mm, inset: (x: 5mm, y: 2.6mm), image("../assets/logo_duon.png", height: 5.2mm)))
