#!/bin/bash
# UserPromptSubmit hook: SUGGESTION MODE 감지 시 stderr에 레이블 출력

input=$(cat)

if echo "$input" | grep -q "SUGGESTION MODE"; then
    echo "💡 [Suggestion Mode] Claude Code 자동 입력 예측이 포함됨 (tengu_prompt_suggestion)" >&2
fi
