#!/bin/bash
# Stop 훅: 커밋 안 된 변경사항이 있으면 Claude에게 커밋하도록 block

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')

# 재진입 방지 (이미 커밋 처리 중이면 통과)
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

cd "$CWD" 2>/dev/null || exit 0

# git 레포가 아니면 통과
git rev-parse --is-inside-work-tree &>/dev/null || exit 0

# 변경사항 확인
HAS_CHANGES=false

# staged/unstaged 변경
git diff --quiet 2>/dev/null || HAS_CHANGES=true
git diff --cached --quiet 2>/dev/null || HAS_CHANGES=true

# untracked 파일
if [ "$HAS_CHANGES" = "false" ]; then
  UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null)
  [ -n "$UNTRACKED" ] && HAS_CHANGES=true
fi

# 변경 없으면 통과
[ "$HAS_CHANGES" = "false" ] && exit 0

# 변경 있으면 block → Claude가 커밋 처리
echo '{"decision":"block","reason":"커밋되지 않은 변경사항이 있습니다. /commit 플로우를 실행하세요 (워크로그 작성 포함)."}'
