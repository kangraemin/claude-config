# Git Rules

모든 git 관련 command와 agent가 따르는 규칙.

---

## 1. 커밋 규칙

### 메시지 형식
```
분류: 한글 설명

상세 설명 (선택)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

### 언어
- **한글로 작성한다.**
- type(분류)만 영어, 나머지는 전부 한글.

### 분류 (type)
- `feat`: 새 기능 추가
- `fix`: 버그 수정
- `refactor`: 리팩토링 (동작 변경 없음)
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정, 의존성
- `docs`: 문서 작업
- `style`: 포맷팅 (코드 변경 없음)
- `perf`: 성능 개선

### 설명 (description)
- **무엇을 왜 변경했는지** 명확하게 적는다.
- 단순 "수정" 금지. 구체적으로 적는다.
- 50자 이내 권장.

**좋은 예:**
```
feat: 자연어 시맨틱 검색 기능 추가
fix: Share Extension에서 URL 파싱 실패하는 문제 수정
refactor: 요약 서비스 Protocol 분리 및 DI 적용
docs: 개발 가이드에 테스트 규칙 추가
test: 빈 쿼리 입력 시 전체 결과 반환 테스트 추가
chore: TCA 1.x → 2.0 업데이트
```

**나쁜 예:**
```
수정                          ← 뭘 수정했는지 모름
검색 관련 작업                  ← 추가인지 수정인지 모름
fix: bug fix                  ← 영어, 내용 없음
여러가지 수정                   ← 커밋 분리 안 함
```

### 본문 (선택)
- 변경 이유가 자명하지 않을 때 작성한다.
- "왜" 이 변경을 했는지 적는다.
- 관련 이슈가 있으면 `Closes #123` 형태로 연결.

### 스테이징 규칙
- 변경된 파일만 개별적으로 `git add` (절대 `git add .` 또는 `git add -A` 금지)
- 민감 파일 제외: `.env`, `credentials`, `*.key`, `*.pem`, `Secrets/`
- 의미 단위로 커밋 분리 (한 커밋에 여러 관심사 넣지 않기)

### 커밋 메시지 전달
- 반드시 HEREDOC 사용:
```bash
git commit -m "$(cat <<'EOF'
feat: 자연어 시맨틱 검색 기능 추가

NLContextualEmbedding 기반 벡터 유사도 검색 구현

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## 2. 푸시 규칙

### 안전 규칙
- `--force` 절대 금지 (force-push 필요 시 사용자 확인 필수)
- `main`/`master` 브랜치에 직접 force push 금지
- upstream이 없으면 `-u origin <branch>`로 설정

### 푸시 전 확인
- 커밋 안 된 변경사항이 있으면 사용자에게 알림
- 푸시할 커밋이 없으면 알림

---

## 3. PR 규칙

### 제목
- 70자 이내
- 커밋 분류와 동일한 형식: `feat: 자연어 시맨틱 검색 기능 추가`
- **한글로 작성한다.**

### 본문
```markdown
## 작업 내용
- 이번 PR에서 한 작업을 bullet point로 정리
- 무엇을 추가/수정/삭제했는지 구체적으로

## 주요 리뷰 포인트
- 리뷰어가 특히 봐야 할 부분
- 설계 결정에 대한 의견이 필요한 부분
- 성능/보안 관점에서 확인이 필요한 부분

## 변경 파일 요약
- `파일명`: 변경 이유 한 줄 설명 (주요 파일만)

## 테스트
- [ ] 추가/수정된 테스트 목록
- [ ] 수동 테스트 항목

## 참고
- 관련 이슈, 문서, 스크린샷 등 (선택)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### PR 전 확인
- 리모트에 브랜치 푸시 확인
- base branch 자동 감지 (main 또는 develop)
- 변경 이력 전체 분석 (최신 커밋만이 아닌 브랜치 전체)

---

## 4. 브랜치 규칙

### 네이밍
- `main`: 항상 빌드 성공 상태
- `develop`: 개발 통합 브랜치
- `feature/<이름>`: 기능 개발
- `fix/<이름>`: 버그 수정
- `chore/<이름>`: 설정/인프라

### 삭제
- 머지된 브랜치는 삭제 (로컬 + 리모트)
- 삭제 전 사용자 확인

---

## 5. 금지 사항

- `git reset --hard` — 사용자 명시적 요청 없이 금지
- `git clean -f` — 사용자 명시적 요청 없이 금지
- `git checkout .` / `git restore .` — 사용자 명시적 요청 없이 금지
- `--no-verify` — 사용자 명시적 요청 없이 금지
- `--force` — 사용자 명시적 요청 없이 금지
- `-i` (interactive) 플래그 — 지원 불가
- 빈 커밋 (`--allow-empty`) — 의미 없는 커밋 금지
