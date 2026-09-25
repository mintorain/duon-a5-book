---
name: duon-a5-book
description: 두온교육 A5(148×210) 전자책 PDF 제작 — 저자가 준 원고 PDF를 원문 무수정으로 옮겨 bookforge practical-a5 스타일(KoPub 돋움, 런인 장 머리, 부 전면 간지, 실습 프롬프트 패널, 2쪽 목차, 저자 카드, QR 특별선물 면, 두온 판권·로고)로 재조판하고 QC 게이트·북마크·도서정보까지 마친다. "A5 도서 제작", "A5 전자책 만들어줘", "원고를 A5로 조판", "두온교육 스타일로 책 만들어줘", "지난번 글로벌 마케팅 책 스타일로", "출판용 PDF로 만들어줘" 같은 요청에 사용. 주제만 있고 원고가 없으면 bookforge 스킬(topic 모드)을 쓴다.
---

# 두온교육 A5 도서 제작 (duon-a5-book)

원고 PDF → A5 상업도서급 전자책 PDF. 첫 적용작: 최재용 『AI 에이전트 활용 글로벌 마케팅』(84쪽, 2026-09-24).
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

작업 폴더(원고가 있는 폴더)에서 확인: 원고 PDF, 표지 이미지, 추가 요청 메모(txt), QR 이미지, 저자 사진, ISBN, 발행일, 판매가. 없는 것은 목록으로 한 번에 묻는다(발행일·ISBN·판매가는 뒤 단계에서 채워도 된다).

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

## 4. 변환 + 원문 검증

```bash
python3 <SK>/scripts/pdf2chapters.py <슬러그>
```
`OK 원문 ↔ md 일치` 가 나와야 다음으로 간다. FAIL 이면 첫 차이 위치를 보고 `sizes`·`full_x1`·`para_gap` 을 조정한다. WARN 의 "예상 밖 급수"는 역할 배정 누락 신호다.

## 5. 출판용 원고 정리

서브에이전트(general-purpose)에게 `chapters/*.md` 전부를 읽혀 `references/publishing.md` §1 기준의 삭제 후보를 JSON 으로 받는다. 키워드(`원고|집필|출판 전|수록했|제공|010-`)로 한 번 더 훑어 누락을 확인하고, 본문 어휘는 제외한다. 확정분을 `deletions.json` 에 넣고 4단계를 다시 돌려 검증 OK 를 확인한다. 지운 문구는 작업 폴더 `출판용_정리_문구.md`에 원문 보관.

## 6. 표지

사용자가 원본 유지 재배치를 원하면 힉스필드 절차(`references/publishing.md` §3). 이미 A5 용 표지가 있으면 그대로 `assets/cover.png`.

## 7. 빌드 → QC 게이트 → 수정 반복

```bash
python3 ~/bookforge/scripts/build.py <슬러그>
(cd <슬러그> && typst compile --root . --font-path ~/bookforge/assets/fonts --ignore-system-fonts typeset/main.typ draft/_c.pdf; rm -f draft/_c.pdf)   # 수렴 경고 확인
python3 ~/bookforge/scripts/qc_gate.py <슬러그>      # PASS 면 final/<슬러그>.pdf
```
FAIL 이면 `gate-report.json` 과 `references/pitfalls.md` 로 원인을 찾는다. 원고를 고쳐 맞추지 않는다(구조·여백으로). `CH_CLOSE_APPROVED` 등 사람 승인 코드는 사용자 승인 없이 쓰지 않는다.

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
| 표 | 열 자연 폭 비례 배분(12~64mm), 위아래 1행 |
| 목차 | 정확히 2쪽, 1fr 분배로 판면 꽉 참, 부 경계에서 자동 분할 |
| 앞부속 | 표지(contain) · 속표지(로고) · 목차 · 저자 소개 카드(`::: quote`, 사진, 무번호) → 본문 1쪽 |
| 뒷부속 | 특별 선물 QR 카드(`::: warn`, QR 42mm, 차례 행 있음·북마크는 finalize 가 추가) · 판권(`colophon`) |
