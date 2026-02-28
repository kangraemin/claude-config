# Git Rules

> **로컬 오버라이드**: 프로젝트에 `.claude/rules/git-rules.md`가 있으면 이 파일 대신 그것을 따른다.
> `COMMIT_LANG=en` 환경변수가 설정되어 있으면 커밋 메시지를 영어로 작성한다.

## 커밋

- **커밋 언어**: `COMMIT_LANG=en`이면 영어, 기본값(ko)이면 **한글**
- type만 영어: `feat: 한글 설명` 또는 `feat: English description` (50자 이내)
- type: feat/fix/refactor/test/chore/docs/style/perf
- 무엇을 왜 변경했는지 구체적으로. "수정" 같은 모호한 표현 금지.
- 본문(선택): 변경 이유가 자명하지 않을 때 "왜"를 적는다.
- HEREDOC 필수:
```bash
git commit -m "$(cat <<'EOF'
feat: 설명

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### 스테이징
- 파일 개별 `git add` (절대 `git add .` / `-A` 금지)
- 민감 파일 제외: `.env`, `credentials`, `*.key`, `*.pem`
- 의미 단위로 커밋 분리

## 푸시
- **커밋하면 반드시 푸시.** 커밋만 하고 안 푸시 금지.
- `--force` 금지 (사용자 확인 필수)
- upstream 없으면 `-u origin <branch>`

## PR
- 제목: 70자 이내, 한글, 커밋 형식과 동일
- 본문:
```markdown
## 작업 내용
- bullet point 정리

## 주요 리뷰 포인트
- 리뷰어가 봐야 할 부분

## 변경 파일 요약
- `파일명`: 변경 이유

## 테스트
- [ ] 테스트 항목

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
- base branch 자동 감지, 브랜치 전체 이력 분석

## 브랜치
- `feature/<이름>`, `fix/<이름>`, `chore/<이름>`
- 머지 후 삭제 (사용자 확인)

## 금지
- `reset --hard`, `clean -f`, `checkout .`, `restore .` — 사용자 요청 없이 금지
- `--no-verify`, `--force`, `-i`(interactive), `--allow-empty` 금지
