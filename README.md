# duon-a5-book

두온교육 A5(148×210mm) 전자책 제작 스킬(Claude Code). 저자 원고 PDF를 원문 무수정으로 옮겨 bookforge `practical-a5` 스타일로 재조판하고, QC 게이트·북마크·판권·도서정보까지 마칩니다. 사용법과 절차는 [SKILL.md](SKILL.md).

## 설치

```bash
# 1) 스킬
git clone https://github.com/mintorain/duon-a5-book ~/.claude/skills/duon-a5-book

# 2) 조판 엔진(bookforge 포크, A5 스타일 팩 포함)
git clone https://github.com/mintorain/bookforge ~/bookforge
git -C ~/bookforge checkout feature/practical-a5

# 3) 서체 — KoPubWorld 돋움(재배포 불가라 저장소에 없음)
#    한국출판인회의 배포본을 받아 아래 이름으로 둔다
#    ~/bookforge/assets/fonts/KoPubWorldDotum-{Light,Medium,Bold}.ttf

# 4) 의존성: Typst 0.14.x, Python 3 + PyMuPDF·markdown-it-py (bookforge SKILL.md '실행 전 점검')
```

## 구성

| 경로 | 내용 |
|---|---|
| `SKILL.md` | 10단계 제작 절차, 디자인 규격 |
| `scripts/` | `profile_pdf.py` 원고 실측 · `pdf2chapters.py` 변환·원문 검증 · `montage.py` 몽타주 · `finalize_pdf.py` 북마크·문서 정보 |
| `templates/book.json` | 책 설정 틀(두온교육 판권 표준 포함) |
| `references/` | `pitfalls.md` 조판 함정과 해법 · `publishing.md` 삭제 기준·판권·표지·도서정보·라이선스 |
| `assets/logo_duonedu.png` | 두온교육 로고 |

## 라이선스·권리

- 스크립트·문서: © 2026 두온교육(mintorain). 내부 사용 목적의 비공개 저장소.
- 두온교육 로고는 두온교육의 자산이며 이 스킬로 만드는 두온교육 도서에만 씁니다.
- bookforge 는 gongnyang/bookforge(MIT)의 포크입니다(원 저작권 고지는 그 저장소 LICENSE·NOTICE.md).
