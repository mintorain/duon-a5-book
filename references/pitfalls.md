# 조판 함정과 해법 (2026-09-24 『AI 에이전트 활용 글로벌 마케팅』 실측)

게이트가 FAIL 하면 먼저 이 목록에서 같은 증상을 찾는다. 대부분 practical-a5 테마에 이미 해법이 들어 있다.

| 증상 | 원인 | 해법 |
|---|---|---|
| 모든 장 머리 위에 13mm 빈 띠, G7-FRAME 드리프트 | 북마크용 숨은 제목 `hide(block(heading))`이 heading 위아래 간격을 흐름에 남김 | `place(top + left, hide(heading(...)))` 로 흐름 밖에 |
| `layout did not converge`, 목차 쪽번호 1~2쪽 어긋남(G14-A) | `here().position()` 으로 남은 공간을 재서 pagebreak | 고정 높이 예약 블록 `block(height: 48mm, breakable:false)` + `v(-48mm)` 를 sticky 머리 **뒤**에 |
| 면 맨 위 장 머리가 36pt 내려앉음 | 예약 블록을 머리 **앞**에 두면 앞 문단 간격이 새 면으로 따라감 | 예약 블록은 머리 뒤 |
| 부 앞 짧은 꼬리 면(패널 하나만), G7-TAIL HARD | 장이 전부 패널로 끝나는 원고 + 부 강제 개면 | 부를 **전면 간지 단독 면**으로 — 앞 면은 '다음 면 통짜 블록' 밀림 면제 |
| 간지가 전면 도판으로 인식 안 됨 | 판형 크기 색면 1장이 흰 바탕과 같은 bbox → qc '가구'로 제거 | 겹치는 두 장(0~106mm, 104~210mm)으로 그림 |
| 책 끝 단독 부속 면(특별 선물) 앞 면이 짧은 꼬리 | 부속 면을 장(heading)으로 둠 | 장이 아닌 카드(`::: warn`), 카드가 면 맨 위에서 시작(2pt 이하 괘선은 객체로 안 잡힘) |
| 부속 면 앞 면이 mid HARD(밀림 면제 실패) | 카드 높이 + 3행 < 앞 면 남은 공간 | 카드를 키움(QR 42mm 등) |
| 두 장이 같은 면에서 시작하면 뒤 장 전부 G14-A 오탐 | qc_gate 가 set 기반 ch_starts 를 넘김 | 포크 qc_gate 패치(북마크 순서 정렬) 필요 — mintorain/bookforge |
| 판권면이 본문 면으로 판정 | qc 판권 식별이 "bookforge"+"조판" 문자열뿐 | 포크 qc_gate 패치: "ISBN"+("펴낸곳"\|"발행인")도 판권 |
| KoPub 으로 바꾸자 행송 16pt 로 줄어듦 | KoPub 행 상자가 작다 | 20.55pt(24행) = `body-leading: 1.597em`, 18.28pt = 1.365em |
| 목차 표제 괘선이 "차례" 글자에 붙음 | 23pt 표제의 흐름 배치 | `place()` 고정 좌표 |
| 간지 제목 "준비하/기" 음절 중간 줄바꿈 | content 본문엔 keep-words 가 안 먹음 | `show regex("\S+"): it => box(it)` |
| 짧은 프롬프트 패널이 두 면으로 쪼개짐 | breakable 패널 | measure 해서 78mm 이하면 breakable:false |
| Bash heredoc 으로 파이썬 패치 시 SyntaxError, JSON 파싱 실패 | Git Bash 가 따옴표 heredoc 안의 `\n`·`\\` 도 풀어 버림 | 이스케이프가 든 소스·JSON 은 Write/Edit 도구로 |
| Windows python 이 `/tmp/...` 를 못 찾음 | Git Bash 경로 | `cygpath -w` 로 바꿔 넘기거나 작업 폴더 상대경로 |
| refit.py 가 "해 없음" | 자간 레버는 1행 미만만 움직임 | 구조(여백·예약·간지)로 해결, 원고는 건드리지 않음 |
| 중제목이 앞 문단에 붙어 보임(실측 15pt < 문단 간격 31pt) | 제목 위 여백을 약한 v() 로 주면 앞 간격과 겹칠 때 작은 쪽으로 정리됨 | 제목 블록 자신의 `above`/`below` 로(h2-above 2.35행) |
| 장 제목 → 중제목이 68pt 로 벌어짐 | 장 제목 블록 below 와 중제목 above 가 예약 블록을 사이에 두고 더해짐 | 장 제목 뒤는 `v(ch-head-below, weak: true)` — 약한 간격이 중제목 above 를 대신 |
| 패널 뒤 문단이 3pt 로 붙음 / 패널 뒤 중제목이 23pt | 패널 뒤 간격을 없애거나 외부 v() 로 줌 | 패널 블록 자체의 `below: grid-pitch` |
| 여백을 바꾼 뒤 G7-MID(85%) 한 면 | 3줄 문단이 외톨이 줄 규칙으로 통째 이동 | refit 안 되면 여백 상수를 ±0.1행 스윕해 통과 조합 선택 |
| 여백 실측 | 눈대중 금지 | 줄 bbox 간격을 급수 쌍(9.8→11.3 등)별로 중앙값 측정 |
