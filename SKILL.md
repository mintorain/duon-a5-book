---
name: duon-a5-book
description: 두온교육 A5(148×210) 전자책 PDF 제작 — 저자가 준 원고(PDF 또는 한글 HWPX)를 원문 무수정으로 옮겨 bookforge practical-a5 스타일(KoPub 돋움, 런인 장 머리, 부 전면 간지, 실습 프롬프트 패널, 2쪽 목차, 저자 카드, QR 특별선물 면, 두온 판권·로고)로 재조판하고 QC 게이트·북마크·도서정보까지 마친다. "A5 도서 제작", "A5 전자책 만들어줘", "원고를 A5로 조판", "두온교육 스타일로 책 만들어줘", "지난번 글로벌 마케팅 책 스타일로", "출판용 PDF로 만들어줘", "한글 문서를 전자책으로", "hwpx 원고를 A5 PDF로", "POD 종이책 표지 만들어줘", "책등 사이즈 알려줘", "날개 표지 펼침면", "디자이너 펼침 표지 점검", "종이책 POD 내지와 전자책 같이", "장표지 추가" 같은 요청에 사용(종이책 표지는 아르떼 210g 날개 표지·백색모조 100g 내지 기본). 주제만 있고 원고가 없으면 bookforge 스킬(topic 모드)을 쓴다.
---

# 두온교육 A5 도서 제작 (duon-a5-book)

원고 PDF·HWPX → A5 상업도서급 전자책 PDF. 첫 적용작: 최재용 『AI 에이전트 활용 글로벌 마케팅』(PDF 원고, 84쪽, 2026-09-24) · 김은아 『AI는 우리 브랜드를 어떻게 말하는가』(HWPX 원고·표 85개, 167쪽, 2026-09-26).
**원칙: 원고 문장은 바꾸지 않는다.** 바꾸는 것은 디자인과, 사용자가 승인한 삭제(`deletions.json`)·추가(저자 약력·특별 선물)뿐이며 변환기가 매번 문자 단위로 검증한다.

`<SK>` = 이 스킬 폴더(`~/.claude/skills/duon-a5-book`), `<BF>` = bookforge(`~/bookforge`, 포크 mintorain/bookforge 의 `feature/practical-a5` 브랜치).
모든 python 호출 앞에 `PYTHONUTF8=1`. 한글 결과는 콘솔 대신 파일로 쓰고 Read 로 본다.

## 0. 사전 점검 (빠뜨리면 빌드가 조용히 틀어진다)

```bash
typst --version                                  # 0.14.x
git -C ~/bookforge branch --show-current          # feature/practical-a5
ls ~/bookforge/styles/practical-a5/theme.typ
ls ~/bookforge/assets/fonts/KoPubWorldDotum-{Light,Medium,Bold}.ttf   # 없으면 아래
```
KoPub 폰트가 없으면 `%LOCALAPPDATA%/Microsoft/Windows/Fonts/KoPubWorld Dotum *.ttf` 를 `KoPubWorldDotum-{Light,Medium,Bold}.ttf` 로 복사(재배포 금지라 저장소엔 없다). bookforge 가 없거나 브랜치가 다르면 `git clone https://github.com/mintorain/bookforge ~/bookforge && git -C ~/bookforge checkout feature/practical-a5`.

## 1. 입력 받기

작업 폴더(원고가 있는 폴더)에서 확인: 원고(PDF 또는 .hwpx — HWPX 면 3·4단계는 **HWPX 경로**), 표지 이미지, 추가 요청 메모(txt), QR 이미지, 저자 사진, ISBN, 발행일, 판매가. 없는 것은 목록으로 한 번에 묻는다(발행일·ISBN·판매가는 뒤 단계에서 채워도 된다).

## 2. 책 프로젝트 만들기

```bash
mkdir -p <work>/<영문-슬러그>/{assets,chapters,diagrams,qc,tools}
cp <SK>/templates/book.json <work>/<슬러그>/book.json
cp <SK>/assets/logo_duonedu.png <work>/<슬러그>/assets/logo_duon.png
```
`assets/`에 `cover.png`(표지), `qr.png`, `author.png`(저자 사진, 이전 도서 PDF 에서 추출 가능)를 넣는다. 폴더명은 영문(최종 PDF 파일명이 폴더명).

## 3. 원고 프로파일 → 설정

```bash
python3 <SK>/scripts/profile_pdf.py <원고.pdf> <슬러그>/qc/profile.txt
```
결과를 Read 해서 `book.json` 의 `manuscript` 를 채운다: `source`, `skip_pages`(표지·원고 목차), `sizes`(chapter/part/section/panel/body/ref/running_head), `full_x1`, `prompt_title_regex`, `author_title`, `gift`(추가 요청의 특별 선물 문구·URL). 템플릿 값은 첫 책의 실측값이다. 서지값(`title`·`colophon` 등)도 채운다 — 판권 표준은 `references/publishing.md` §2.

### HWPX 원고일 때 (3단계 대신)

```bash
python3 <SK>/scripts/hwpx2chapters.py <슬러그> --profile    # -> qc/hwpx_profile.txt
```
`book.json` `manuscript` 에 `"source": "../원고.hwpx"` 와, 실측과 다를 때만 `"hwpx": {...}` 를 넣는다.
한글 원고는 스타일이 "바탕글" 하나뿐인 경우가 많아 역할을 **글자 크기·전체 굵게·왼쪽 여백(HWPUNIT)** 으로 가른다.
프로파일 표에서 읽을 것: 장(가장 큰 굵은 크기, 쪽나눔) · 절 · 소제목 크기, 인용·코드·글머리 여백, 표 열 수 분포, 병합 셀 경고.

| `hwpx` 키 | 기본값 | 뜻 |
|---|---|---|
| `body_start_text` | 자동(차례 스타일 다음 첫 장 크기 문단) | 본문 첫 장 제목 |
| `chapter`·`section`·`subsection` | 16 · 12 · 10.5 | 전체 굵은 문단의 pt → `#`·`##`·`###` |
| `indents` | quote 1134 · code 567 · bullet 425 | 왼쪽 여백 → `>` · ``` · `-` |
| `bullet_glyph` | `"· "` | 글머리 글자(목록 표지로 바뀜) |
| `caption_regex` | `^그림 (\d+)\.\s` | 그림 바로 다음 캡션 문단 |
| `transpose_min_cols` | 9 | 이 열 수 이상 표는 행·열을 바꿔 A5 폭에 싣는다(글자 불변) |
| `author_title` | `"지은이"` | 이 장은 앞부속 저자 소개 카드로 |
| `korean_outline` | false | 절·소제목 십진 번호(1.1 / 2.3.1)를 한국식(1. / 1))으로 — 두온 POD 원고서식(개요2 "1." / 개요3 "1)")과 같음, **원고 글자 변경, 요청·승인 시에만**. 바뀐 목록은 `qc/outline_numbering.txt` |
| `fig_renumber` | false | 캡션 번호를 등장순으로 — **원고 글자 변경, 사용자 승인 후에만** |

## 4. 변환 + 원문 검증

HWPX 는 `python3 <SK>/scripts/hwpx2chapters.py <슬러그>` — 원문 대조(순서까지)·굵게 파싱 수·캡션 없는 끝 그림(로고) 버림·역할 미배정 굵은 크기를 함께 보고한다.


```bash
python3 <SK>/scripts/pdf2chapters.py <슬러그>
```
`OK 원문 ↔ md 일치` 가 나와야 다음으로 간다. FAIL 이면 첫 차이 위치를 보고 `sizes`·`full_x1`·`para_gap` 을 조정한다. WARN 의 "예상 밖 급수"는 역할 배정 누락 신호다.

## 5. 출판용 원고 정리

서브에이전트(general-purpose)에게 `chapters/*.md` 전부를 읽혀 `references/publishing.md` §1 기준의 삭제 후보를 JSON 으로 받는다. 키워드(`원고|집필|출판 전|수록했|제공|010-`)로 한 번 더 훑어 누락을 확인하고, 본문 어휘는 제외한다. 확정분을 `deletions.json` 에 넣고 4단계를 다시 돌려 검증 OK 를 확인한다. 지운 문구는 작업 폴더 `출판용_정리_문구.md`에 원문 보관.

## 6. 표지

사용자가 원본 유지 재배치를 원하면 힉스필드 절차(`references/publishing.md` §3). 이미 A5 용 표지가 있으면 그대로 `assets/cover.png`.
표지가 아예 없으면 `<SK>/templates/cover.typ`(크레딧 없음, 글자는 book.json `title`·`subtitle`·`author`·`cover`에서 읽음)를 `tools/`에 복사해 렌더:
`typst compile --root . --font-path ~/bookforge/assets/fonts --ignore-system-fonts --ppi 300 tools/cover.typ assets/cover.png`.
`cover.label`·`tagline`·`question`·`highlight` 는 원고에 없는 카피라 사용자 확인 항목. 표지를 쓰면 `pageroles.json` = `{"roles":[{"page":1,"code":"FULL_BLEED_PLATE","why":"표지"}]}`.

## 7. 빌드 → QC 게이트 → 수정 반복

```bash
python3 ~/bookforge/scripts/build.py <슬러그>
(cd <슬러그> && typst compile --root . --font-path ~/bookforge/assets/fonts --ignore-system-fonts typeset/main.typ draft/_c.pdf; rm -f draft/_c.pdf)   # 수렴 경고 확인
python3 ~/bookforge/scripts/qc_gate.py <슬러그>      # PASS 면 final/<슬러그>.pdf
```
표가 있는 책은 줄넘침 검사도 돌린다(판면 오른쪽·아래 넘침, 표 칸에서 1~2글자만 떨어진 줄):
```bash
python3 <SK>/scripts/overflow_check.py <슬러그>/draft/book.pdf <슬러그>/qc/overflow.txt   # 넘침 0 이어야
```
FAIL 이면 `gate-report.json` 과 `references/pitfalls.md` 로 원인을 찾는다. 원고를 고쳐 맞추지 않는다(구조·여백으로). `CH_CLOSE_APPROVED` 등 사람 승인 코드는 사용자 승인 없이 쓰지 않는다.
refit·여백 조정으로도 남는 G7-MID/G8 은 목록으로 사용자 승인을 받은 뒤 `qc/gate-exceptions.json`(approved_by·date·reason·fails)에 기록하고 draft 를 `final/<슬러그>.pdf` 로 복사한다. 승인 전 산출물은 파일명에 "검토본".

## 8. 시각 검수 (생략 금지)

```bash
python3 <SK>/scripts/montage.py <슬러그>/final/<슬러그>.pdf <슬러그>/qc               # 18면 몽타주
python3 <SK>/scripts/montage.py <슬러그>/final/<슬러그>.pdf <슬러그>/qc --pages 1,2,3,5,<끝-1>,<끝>
```
몽타주를 Read 로 전부 본다: 표지·속표지 로고·2쪽 목차·저자 카드(무번호)·본문 1쪽 시작·부 간지·표 열 배분·패널·특별 선물·판권. 글자 겹침·빈 면·음절 중간 줄바꿈이 없어야 한다.

## 9. 출판용 마무리

```bash
python3 <SK>/scripts/finalize_pdf.py <슬러그> "<작업폴더>/<도서명>_A5_전자책_vN.pdf"
```
북마크 3단(표지·차례·저자 소개 / 부 → 장 → 절 / 부록 / 특별 선물·판권), 문서 정보(주제에 ISBN), ko-KR, 북마크 창 열림. QR 은 `pip install zxing-cpp` 로 판독해 URL 이 적힌 주소로 가는지 확인(단축 URL 이면 리다이렉트까지).

## 9-1. POD 종이책 표지 (펼침면)

종이책을 내면 **기본 사양으로 표지를 디자인한다**(2026-10-14 이신우 확정): 표지 **아르떼 210g 날개 표지**(날개 100mm) · 내지 **백색모조 100g** · 컬러 · 무선제본. 다른 사양을 말하면 그 값을 쓴다.
책등 = 내지 쪽수 ÷ 2 × 0.12 + 0.5mm (0.5mm 반올림, 194쪽 → 12mm). 인쇄소 값이 오면 그 값이 우선.
뒷날개 | 뒷표지 | 책등 | 앞표지 | 앞날개 펼침면을 `<SK>/scripts/pod_spread.py <책폴더>/POD표지_펼침면.json` 으로 조립한다 → 인쇄용 PDF·300dpi PNG·가이드 PNG.
뒷표지는 종이책 ISBN 바코드 + 정가, 앞날개 저자 소개, 뒷날개 시리즈·출판사. 규격·키 설명·확인 항목은 `references/pod-cover.md`.
디자이너가 펼침 파일을 이미 줬으면 새로 그리지 않고 칸을 잘라 다시 조립한다 → `references/pod-cover.md` §6, `scripts/pod_reassemble.py`.

## 9-2. 종이책 POD 내지 + 전자책 동시 제작 (practical-154, 2026-10-19 황혜진 책)

판형 값 **154×216 은 재단 여유 3mm 포함**이다(완성 148×210). 전자책·종이책 모두 154×216 낱면이며 theme 의 `TT.trim` 이 이미 154×216 — 전면 색면에 6mm 를 더하지 않는다.
참고 구현: 황혜진 책 `hwanghyejin/tools/`(make.sh · post.py · finalize.py · toc_design.typ · ch_divider.typ · pod_cover.py · barcode.typ).

| 항목 | 규칙 |
|---|---|
| 판본 전환 | `sh tools/make.sh [ebook]` → `draft/book_<판본>.pdf` → `tools/finalize.py <판본> <출력>` |
| 종이책 앞부속 | 표지 없음(표지는 따로 인쇄) → 속표지 1쪽(오른쪽 면) · 빈 면 · 차례 표지 3쪽 … |
| 전자책 앞부속 | 표지 1쪽 + **빈 면 2쪽** → 속표지 3쪽. 이후 종이책과 같은 면 배치라 **전자책 n+2쪽 = 종이책 n쪽**, 펼침 보기 짝도 같다(2026-10-19 이신우 지시) |
| 장표지 | 오른쪽(홀수) 면에만. 앞 면이 비면 빈 면(`<bf-pre>`/`<bf-chs>` 표지로 꼬리말·쪽번호 생략). 본문은 장표지 다음 면 맨 위 |
| 판권 | 마지막 왼쪽(짝수) 면 — 쪽수가 홀수면 finalize 가 판권 앞에 빈 면. 종이책 총 쪽수는 짝수 |
| 꼬리말 | 두 판본 모두 PDF 쪽 기준 홀수 오른쪽·짝수 왼쪽(공용 테마 기본값 그대로 — 판본별로 뒤집지 않는다) |
| 판권 값 | 종이책 ISBN·정가 / 전자책은 `book.json ebook.isbn`·`price.ebook` 으로 post.py 가 바꿔 넣음 |
| 전자책 앞·뒤표지 | 디자이너 앞표지 → 154×216 300dpi `assets/cover.png`. 뒤표지 = 펼침 표지의 뒷표지 칸 + 바코드·전자책 정가 |
| 종이책 표지 | 내지 쪽수가 바뀔 때마다 책등을 다시 계산하고 파일명 크기도 바꾼다(166쪽 10.5mm → 180쪽 11.5mm) |

**책별 디자인은 공용 테마를 고치지 않고** `tools/post.py` 가 빌드 사본(`typeset/_style/theme.typ`)을 패치한다:
문자열 치환(색·로고 칩) 또는 함수 구간 통째 교체(`#let toc-row` ~ `#let a5-toc(meta` → toc_design.typ, `#let chapter-cover(` ~ `#let bf-chapter(` → ch_divider.typ).
공용 테마의 연결점(`chapter_cover` 등)을 켜고 함수만 바꿔 끼우는 쪽이 공용 테마 변경에 덜 깨진다.
⚠️ 공용 테마는 다른 세션에서 같은 날에도 바뀐다 — 패치 대상이 없으면 `sys.exit` 로 멈추고, `make.sh | tail` 은 실패를 숨기므로 로그 파일로 받아 확인하고 **draft PDF 시각이 갱신됐는지** 본 뒤 finalize 한다.

검증: 원문 대조 OK(장·그림·글자 수) · 북마크와 차례 쪽번호 일치 · 장표지 홀수 면 · 빈 면에 꼬리말 없음 · 꼬리말 좌우(홀수·짝수 면 글자 좌표) · 종이책 n쪽 = 전자책 n+2쪽 내용 대조(차례·판권 외 차이 0).

## 10. 도서정보와 보고

`book-info` 스킬로 `도서정보_{도서명}_{YYYYMMDD}.md`(ISBN·판매가·키워드·책소개·서평). 보고에는 산출 파일, 삭제/추가 내역, 확인이 필요한 사항(발행일·판매가·KoPub 상업 이용·저자 사진 동의)을 적는다.

## 디자인 규격 (practical-a5, 바꿀 때는 `~/bookforge/styles/practical-a5/theme.typ`)

| 요소 | 규격 |
|---|---|
| 판형·판면 | 148×210mm, 여백 상19/하17/좌16/우14, 행송 20.55pt(24행) |
| 서체 | KoPubWorld 돋움 전부(본문 Medium 9.8pt, 표제 Bold) |
| 장 머리 | 개면 없는 런인(괘선 + CHAPTER NN 라벨 + 대형 번호 + 제목), 아래 본문 5행 보장(48mm 예약), 위 1.2행 |
| 부 | `::: info PART NN` → 남색 전면 간지 단독 면 |
| 여백(실측) | 문단↔문단 31pt · 본문→중제목 43pt · 패널→중제목 51pt · 중제목→본문 11pt · 장 제목→첫 문단 22pt · 장 제목→중제목 20pt. 상수 `h2-above 2.35행`·`h2-below 0.8행`·`ch-head-below 1.0행`(theme.typ 상단) |
| 실습 프롬프트 | `::: tip 제목` 패널, 78mm 이하는 쪼개지 않음, 위아래 1행 |
| 표 | 열 하한 = 칸의 가장 긴 어절 폭, 남는 폭은 (한 줄 폭 − 하한) 비례 · 칸은 어절 단위 줄바꿈 · 판면 55% 이하 표는 쪼개지 않음(긴 표는 머리 행 반복) · 6열 이상 7.6pt · 빈 칸(양식) 높이 확보 · 위아래 1행 |
| 링크 | 긴 URL 은 "/"·"." 뒤에서 줄바꿈(링크 주소는 그대로) |
| 꼬리말(러닝푸터) | **홀수쪽(오른쪽 면) = 오른쪽 정렬**: `장 칩·제목 · 쪽번호`가 오른쪽 끝 / **짝수쪽(왼쪽 면) = 왼쪽 정렬**: `쪽번호 · 장 칩·제목`이 왼쪽 끝 → 펼치면 쪽번호가 바깥쪽(2026-10-19 이신우 확정, 이전 안쪽 배치 폐기). 쪽번호 = PDF 쪽(되감지 않음). 속표지·차례·장표지·빈 면은 꼬리말 없음. theme.typ footer: `if calc.odd(pn) { h(1fr); chap; h(2.6mm); page-no } else { page-no; h(2.6mm); chap; h(1fr) }` (practical-a5·practical-154 반영) |
| 목차 | 정확히 2쪽, 1fr 분배로 판면 꽉 참, 부 경계에서 자동 분할. 장이 적고 절이 많으면 `toc_depth: 2`(장+절, 여러 면으로 흐름) |
| 앞부속 | 표지(contain) · 속표지(로고) · 목차 · 저자 소개 카드(`::: quote`, 사진, 무번호) → 본문 1쪽 |
| 뒷부속 | 특별 선물 QR 카드(`::: warn`, QR 42mm, 차례 행 있음·북마크는 finalize 가 추가) · 판권(`colophon`) |

### book.json 책별 선택 키 (theme 이 읽음, 없으면 기본)

| 키 | 기본 | 쓰는 때 |
|---|---|---|
| `toc_depth` | 1 | 2 = 장 아래 절(`##`)까지 차례에 싣는다 — 장 10개 안팎·절 100개 이상 책 |
| `table_style` | `"plain"` | `"banded"` = 남색 머리 행(흰 글자) + 줄무늬 행 — 표가 많은 실무서 |
| `para_spacing_rows` | 1.0 | 문단 간격(격자 행). 1~2줄 짧은 문단이 많아 G8-STRETCH 가 많으면 0.35~0.5 (쪽수 약 10% 감소) — 규격 변경이라 사용자 확인 |
| `author_card_size` | 10.5 | 약력이 길면 9.8 안팎으로 낮춰 저자 카드를 한 면에 |
| `chapter_numbering` | `"numeric"` | `"korean"` = 장 번호 칩을 "01" 대신 "1장"으로, 차례·장 머리·머리글에서 제목 앞 "N장" 중복을 뗌(차례 행 글자는 원문과 같아 G14 통과) |
| `cover` | — | `templates/cover.typ` 표지 문구(위 6단계) |
| `front_matter` | — | 속표지·차례 색을 표지 디자인에 맞출 때 `{bg, ink, accent, subtitle, mark, rule, muted}` (practical-154 만, 2026-10-19 조아라 책). 없으면 기존 흰 바탕·남색. muted 는 바탕 대비 4.5 이상, accent 는 브랜드 색 계열(G14-B) |
| `chapter_cover` | false | true = 번호 장(N장)마다 단독 장표지 면(front_matter 바탕색·큰 "N장"·제목·절 목록, 쪽번호 없음), 본문은 다음 면 맨 위에서 런인 머리 없이. 차례·북마크 쪽번호는 장표지 면 (practical-154, 2026-10-19 조아라 책) |
| `toc_fill` | false | toc_depth 2 와 함께 true = 차례를 정확히 두 면에, 장 묶음 사이를 벌려 판면을 꽉 채움(장 칩 박스·구분 괘선). 점선 리더는 STYLE 금지라 쓰지 않음. 나눌 장은 `toc_break_before` 로 덮어쓰기 |
| `title_verso_blank` | false | true = 속표지 뒷면(2쪽)을 빈 면으로 — 종이책 쪽 맞춤. QC 는 G3-FIT(앞부속 텍스트 0행)로 걸리는데 빈 면엔 pageroles anchor 를 못 달므로 gate-exceptions 에 기록 (practical-154, 2026-10-19) |
