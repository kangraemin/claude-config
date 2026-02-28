#!/bin/bash
# Claude Code 설정 마법사
# 사용법: bash ~/.claude/scripts/setup.sh [--local]
#   --local: 현재 프로젝트(.claude/settings.json) 설정

set -euo pipefail

LOCAL_MODE=false
if [[ "${1:-}" == "--local" ]]; then
  LOCAL_MODE=true
fi

if $LOCAL_MODE; then
  SETTINGS=".claude/settings.json"
  LABEL="로컬 (현재 프로젝트)"
  mkdir -p .claude
  [[ -f "$SETTINGS" ]] || echo '{}' > "$SETTINGS"
else
  SETTINGS="$HOME/.claude/settings.json"
  LABEL="글로벌"
fi

# jq 체크
if ! command -v jq &>/dev/null; then
  echo "❌ jq가 필요합니다: brew install jq"
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║    Claude Code 설정 마법사           ║"
printf "║    대상: %-29s║\n" "$LABEL"
echo "╚══════════════════════════════════════╝"
echo "엔터: 현재값 유지  |  번호 입력: 변경"
echo ""

# 현재값 읽기
cur_model=$(jq -r '.model // ""' "$SETTINGS")
cur_worklog_timing=$(jq -r '.env.WORKLOG_TIMING // ""' "$SETTINGS")
cur_commit_timing=$(jq -r '.env.COMMIT_TIMING // ""' "$SETTINGS")
cur_tool_search=$(jq -r '.env.ENABLE_TOOL_SEARCH // ""' "$SETTINGS")
cur_commit_lang=$(jq -r '.env.COMMIT_LANG // ""' "$SETTINGS")

# 글로벌 폴백 (로컬 모드일 때)
if $LOCAL_MODE; then
  G="$HOME/.claude/settings.json"
  [[ -z "$cur_model" ]] && cur_model="$(jq -r '.model // "opusplan"' "$G") (글로벌)"
  [[ -z "$cur_worklog_timing" ]] && cur_worklog_timing="$(jq -r '.env.WORKLOG_TIMING // "each-commit"' "$G") (글로벌)"
  [[ -z "$cur_commit_timing" ]] && cur_commit_timing="$(jq -r '.env.COMMIT_TIMING // "session-end"' "$G") (글로벌)"
  [[ -z "$cur_commit_lang" ]] && cur_commit_lang="$(jq -r '.env.COMMIT_LANG // "ko"' "$G") (글로벌)"
else
  [[ -z "$cur_model" ]] && cur_model="opusplan"
  [[ -z "$cur_worklog_timing" ]] && cur_worklog_timing="each-commit"
  [[ -z "$cur_commit_timing" ]] && cur_commit_timing="session-end"
  [[ -z "$cur_commit_lang" ]] && cur_commit_lang="ko"
fi
[[ -z "$cur_tool_search" ]] && cur_tool_search="true"

# 수집할 새 값들
new_model=""
new_worklog_timing=""
new_commit_timing=""
new_commit_lang=""
new_tool_search=""

# --- 1. 모델 (글로벌만) ---
if ! $LOCAL_MODE; then
  echo "1) 모델 [현재: $cur_model]"
  echo "   1) opusplan              — 리드 에이전트 + 팀 모드"
  echo "   2) claude-sonnet-4-6     — 빠르고 저렴"
  echo "   3) claude-haiku-4-5-20251001 — 최경량"
  printf "   선택 (엔터=유지): "
  read -r choice
  case "$choice" in
    1) new_model="opusplan" ;;
    2) new_model="claude-sonnet-4-6" ;;
    3) new_model="claude-haiku-4-5-20251001" ;;
  esac
  echo ""
fi

# --- 2. 워크로그 타이밍 ---
echo "2) 워크로그 작성 시점 [현재: $cur_worklog_timing]"
echo "   1) each-commit  — 커밋할 때마다 자동 작성"
echo "   2) session-end  — 세션 종료 시 한 번 (오늘 작성 안 했으면 요청)"
echo "   3) manual       — /worklog 직접 실행할 때만"
printf "   선택 (엔터=유지): "
read -r choice
case "$choice" in
  1) new_worklog_timing="each-commit" ;;
  2) new_worklog_timing="session-end" ;;
  3) new_worklog_timing="manual" ;;
esac
echo ""

# --- 3. 커밋 타이밍 ---
echo "3) 커밋 시점 [현재: $cur_commit_timing]"
echo "   1) session-end  — 세션 종료 시 미커밋 변경 있으면 자동 요청"
echo "   2) manual       — /commit 직접 실행할 때만"
printf "   선택 (엔터=유지): "
read -r choice
case "$choice" in
  1) new_commit_timing="session-end" ;;
  2) new_commit_timing="manual" ;;
esac
echo ""

# --- 4. 커밋 언어 ---
echo "4) 커밋 메시지 언어 [현재: $cur_commit_lang]"
echo "   1) ko — 한글 (기본)"
echo "   2) en — English"
printf "   선택 (엔터=유지): "
read -r choice
case "$choice" in
  1) new_commit_lang="ko" ;;
  2) new_commit_lang="en" ;;
esac
echo ""

# --- 5. 도구 검색 (글로벌만) ---
if ! $LOCAL_MODE; then
  echo "5) Tool Search [현재: $cur_tool_search]"
  echo "   1) true  — 활성화"
  echo "   2) false — 비활성화"
  printf "   선택 (엔터=유지): "
  read -r choice
  case "$choice" in
    1) new_tool_search="true" ;;
    2) new_tool_search="false" ;;
  esac
  echo ""
fi

# --- settings.json 업데이트 ---
tmp=$(mktemp)
cp "$SETTINGS" "$tmp"

apply_jq() {
  local filter="$1"
  jq "$filter" "$tmp" > "${tmp}.new" && mv "${tmp}.new" "$tmp"
}

[[ -n "$new_model" ]] && apply_jq --arg v "$new_model" '.model = $v'
[[ -n "$new_worklog_timing" ]] && apply_jq --arg v "$new_worklog_timing" '.env.WORKLOG_TIMING = $v'
[[ -n "$new_commit_timing" ]] && apply_jq --arg v "$new_commit_timing" '.env.COMMIT_TIMING = $v'
[[ -n "$new_commit_lang" ]] && apply_jq --arg v "$new_commit_lang" '.env.COMMIT_LANG = $v'
[[ -n "$new_tool_search" ]] && apply_jq --arg v "$new_tool_search" '.env.ENABLE_TOOL_SEARCH = $v'

mv "$tmp" "$SETTINGS"

echo "✅ 저장 완료: $SETTINGS"
[[ -n "$new_model" ]] && echo "   모델: $new_model"
[[ -n "$new_worklog_timing" ]] && echo "   워크로그 시점: $new_worklog_timing"
[[ -n "$new_commit_timing" ]] && echo "   커밋 시점: $new_commit_timing"
[[ -n "$new_commit_lang" ]] && echo "   커밋 언어: $new_commit_lang"
[[ -n "$new_tool_search" ]] && echo "   도구 검색: $new_tool_search"
echo ""
echo "변경사항은 다음 Claude Code 세션부터 적용됩니다."
