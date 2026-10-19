// POD 펼침 표지에 얹을 바코드+정가 조각(투명 바탕, 자동 크기). tools/pod_cover.py 가 부른다.
//   --input isbn=13자리 --input addon=03810 --input price=15,000   (isbn 없으면 바코드 자리 상자)
#let inp = sys.inputs
#let isbn = inp.at("isbn", default: none)
#let addon = inp.at("addon", default: none)
#let price = inp.at("price", default: none)
#set page(width: auto, height: auto, margin: 0pt, fill: none)
#set text(font: "KoPubWorldDotum", lang: "ko")

// ---- EAN-13 + EAN-5 (벡터) ----
#let L = ("0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011")
#let flip(s) = s.clusters().map(c => if c == "0" { "1" } else { "0" }).join()
#let R = L.map(flip)
#let G = R.map(s => s.clusters().rev().join())
#let P13 = ("LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL")
#let P5 = ("GGLLL", "GLGLL", "GLLGL", "GLLLG", "LGGLL", "LLGGL", "LLLGG", "LGLGL", "LGLLG", "LLGLG")
#let enc(d, k) = if k == "L" { L.at(d) } else { G.at(d) }

#let bars(bits, x0, mw, h, y: 0pt, longs: ()) = {
  for (i, b) in bits.clusters().enumerate() {
    if b == "1" {
      let long = longs.any(r => i >= r.at(0) and i < r.at(1))
      place(top + left, dx: x0 + i * mw, dy: y, rect(width: mw + 0.01mm, height: if long { h + 1.6mm } else { h }, fill: black))
    }
  }
}

#let barcode(code, add) = {
  let d = code.clusters().map(int)
  assert(d.len() == 13, message: "ISBN 13자리")
  let s = range(12).map(i => d.at(i) * if calc.odd(i) { 3 } else { 1 }).sum()
  assert(calc.rem(10 - calc.rem(s, 10), 10) == d.at(12), message: "ISBN 체크기호 오류")
  let pat = P13.at(d.at(0))
  let bits = "101" + range(6).map(i => enc(d.at(i + 1), pat.at(i))).join() + "01010" + range(6).map(i => R.at(d.at(i + 7))).join() + "101"
  let mw = 0.30mm
  let bh = 19mm
  let q = 11 * mw                                  // 왼쪽 여백(첫 자리 숫자 자리)
  let w13 = q + 95 * mw
  let add-bits = none
  if add != none {
    let a = add.clusters().map(int)
    let cs = calc.rem(3 * (a.at(0) + a.at(2) + a.at(4)) + 9 * (a.at(1) + a.at(3)), 10)
    let p = P5.at(cs)
    add-bits = "01011" + range(5).map(i => enc(a.at(i), p.at(i))).join("01")
  }
  let wa = if add-bits != none { 9 * mw + add-bits.len() * mw + 5 * mw } else { 7 * mw }
  box(fill: white, inset: (x: 2.5mm, y: 1.5mm), box(width: w13 + wa, height: bh + 6mm + 4mm, {
    let ty0 = 4mm
    set text(font: "KoPubWorldDotum", size: 8pt, fill: black, tracking: 0.05em)
    place(top + left, dx: q, dy: 0.6mm, text(size: 7pt, "ISBN " + code.slice(0, 3) + "-" + code.slice(3, 5) + "-" + code.slice(5, 10) + "-" + code.slice(10, 12) + "-" + code.slice(12)))
    bars(bits, q, mw, bh, y: ty0, longs: ((0, 3), (45, 50), (92, 95)))
    let ty = ty0 + bh + 0.3mm
    place(top + left, dx: 0pt, dy: ty, text(str(d.at(0))))
    place(top + left, dx: q + 3 * mw, dy: ty, box(width: 42 * mw, align(center, text(code.slice(1, 7).clusters().join(h(0.6mm))))))
    place(top + left, dx: q + 50 * mw, dy: ty, box(width: 42 * mw, align(center, text(code.slice(7).clusters().join(h(0.6mm))))))
    if add-bits != none {
      let ax = w13 + 9 * mw
      place(top + left, dx: ax, dy: ty0 - 0.2mm, box(width: add-bits.len() * mw, align(center, text(size: 8pt, add.clusters().join(h(0.6mm))))))
      bars(add-bits, ax, mw, bh - 2.4mm, y: ty0 + 3.2mm)
    }
  }))
}

#{
  if isbn != none { barcode(isbn, addon) } else {
    box(width: 52mm, height: 30mm, fill: white, align(center + horizon,
      text(size: 8pt, fill: rgb("#555555"), [ISBN 바코드 자리])))
  }
  v(1.8mm)
  text(size: 9.5pt, weight: "bold", fill: white, if price != none { [값 #(price)원] } else { [값 NN,000원] })
}
