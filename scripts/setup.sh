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
echo "║    대상: $LABEL"
echo "╚══════════════════════════════════════╝"
echo "엔터: 현재값 유지  |  번호 입력: 변경"
echo ""

# 현재값 읽기
cur_model=$(jq -r '.model // ""' "$SETTINGS")
cur_worklog=$(jq -r '.env.WORKLOG_MODE // ""' "$SETTINGS")
cur_tool_search=$(jq -r '.env.ENABLE_TOOL_SEARCH // ""' "$SETTINGS")
cur_commit_lang=$(jq -r '.env.COMMIT_LANG // ""' "$SETTINGS")

# 글로벌 폴백 (로컬 모드일 때)
if $LOCAL_MODE; then
  [[ -z "$cur_model" ]] && cur_model=$(jq -r '.model // "opusplan"' "$HOME/.claude/settings.json") && cur_model="${cur_model} (글로벌)"
  [[ -z "$cur_worklog" ]] && cur_worklog=$(jq -r '.env.WORKLOG_MODE // "all"' "$HOME/.claude/settings.json") && cur_worklog="${cur_worklog} (글로벌)"
  [[ -z "$cur_commit_lang" ]] && cur_commit_lang=$(jq -r '.env.COMMIT_LANG // "ko"' "$HOME/.claude/settings.json") && cur_commit_lang="${cur_commit_lang} (글로벌)"
else
  [[ -z "$cur_model" ]] && cur_model="opusplan"
  [[ -z "$cur_worklog" ]] && cur_worklog="all"
  [[ -z "$cur_commit_lang" ]] && cur_commit_lang="ko"
fi
[[ -z "$cur_tool_search" ]] && cur_tool_search="true"

# --- 1. 모델 (로컬 모드에서는 건너뜀) ---
new_model=""
if ! $LOCAL_MODE; then
  echo "1) 모델 [현재: $cur_model]"
  echo "   1) opusplan       — 리드 에이전트 + 팀 모드"
  echo "   2) claude-sonnet-4-6 — 빠르고 저렴"
  echo "   3) claude-haiku-4-5-20251001 — 최경량"
  printf "   선택 (엔터=유지): "
  read -r choice
  case "$choice" in
    1) new_model="opusplan" ;;
    2) new_model="claude-sonnet-4-6" ;;
    3) new_model="claude-haiku-4-5-20251001" ;;
    *) new_model="" ;;
  esac
  echo ""
fi

# --- 2. 워크로그 모드 ---
echo "2) 워크로그 모드 [현재: $cur_worklog]"
echo "   1) all    — 모든 커밋에 자동 기록"
echo "   2) off    — 워크로그 끄기"
echo "   3) manual — /worklog 수동 실행만"
printf "   선택 (엔터=유지): "
read -r choice
case "$choice" in
  1) new_worklog="all" ;;
  2) new_worklog="off" ;;
  3) new_worklog="manual" ;;
  *) new_worklog="" ;;
esac
echo ""

# --- 3. 커밋 언어 ---
echo "3) 커밋 메시지 언어 [현재: $cur_commit_lang]"
echo "   1) ko — 한글 (기본)"
echo "   2) en — English"
printf "   선택 (엔터=유지): "
read -r choice
case "$choice" in
  1) new_commit_lang="ko" ;;
  2) new_commit_lang="en" ;;
  *) new_commit_lang="" ;;
esac
echo ""

# --- 4. 도구 검색 (글로벌만) ---
new_tool_search=""
if ! $LOCAL_MODE; then
  echo "4) Tool Search [현재: $cur_tool_search]"
  echo "   1) true  — 활성화"
  echo "   2) false — 비활성화"
  printf "   선택 (엔터=유지): "
  read -r choice
  case "$choice" in
    1) new_tool_search="true" ;;
    2) new_tool_search="false" ;;
    *) new_tool_search="" ;;
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
[[ -n "$new_worklog" ]] && apply_jq --arg v "$new_worklog" '.env.WORKLOG_MODE = $v'
[[ -n "$new_commit_lang" ]] && apply_jq --arg v "$new_commit_lang" '.env.COMMIT_LANG = $v'
[[ -n "$new_tool_search" ]] && apply_jq --arg v "$new_tool_search" '.env.ENABLE_TOOL_SEARCH = $v'

mv "$tmp" "$SETTINGS"

echo "✅ 저장 완료: $SETTINGS"
[[ -n "$new_model" ]] && echo "   모델: $new_model"
[[ -n "$new_worklog" ]] && echo "   워크로그: $new_worklog"
[[ -n "$new_commit_lang" ]] && echo "   커밋 언어: $new_commit_lang"
[[ -n "$new_tool_search" ]] && echo "   도구 검색: $new_tool_search"
echo ""
echo "변경사항은 다음 Claude Code 세션부터 적용됩니다."
