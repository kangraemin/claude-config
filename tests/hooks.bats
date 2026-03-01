#!/usr/bin/env bats
# Hook tests: auto-commit.sh, worklog.sh flag branching

setup() {
  TEST_DIR="$(mktemp -d)"
  cd "$TEST_DIR"
  git init -q
  git commit --allow-empty -m "init" -q
  HOOKS_DIR="$HOME/.claude/hooks"
}

teardown() {
  rm -rf "$TEST_DIR"
}

# --- auto-commit.sh ---

@test "auto-commit: no changes - no block" {
  INPUT='{"cwd":"'"$TEST_DIR"'","stop_hook_active":false}'
  run bash -c "echo '$INPUT' | COMMIT_TIMING=session-end WORKLOG_TIMING=each-commit $HOOKS_DIR/auto-commit.sh"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "auto-commit: uncommitted changes - block" {
  echo "hello" > "$TEST_DIR/test.txt"
  git add test.txt
  INPUT='{"cwd":"'"$TEST_DIR"'","stop_hook_active":false}'
  run bash -c "echo '$INPUT' | COMMIT_TIMING=session-end WORKLOG_TIMING=manual $HOOKS_DIR/auto-commit.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"block"* ]]
  [[ "$output" == *"/commit"* ]]
}

@test "auto-commit: GIT_TRACK=true + TIMING=each-commit includes worklog msg" {
  echo "hello" > "$TEST_DIR/test.txt"
  git add test.txt
  INPUT='{"cwd":"'"$TEST_DIR"'","stop_hook_active":false}'
  run bash -c "echo '$INPUT' | COMMIT_TIMING=session-end WORKLOG_TIMING=each-commit WORKLOG_GIT_TRACK=true $HOOKS_DIR/auto-commit.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"block"* ]]
  # Korean message check
  echo "$output" | grep -q "포함"
}

@test "auto-commit: GIT_TRACK=false excludes worklog msg" {
  echo "hello" > "$TEST_DIR/test.txt"
  git add test.txt
  INPUT='{"cwd":"'"$TEST_DIR"'","stop_hook_active":false}'
  run bash -c "echo '$INPUT' | COMMIT_TIMING=session-end WORKLOG_TIMING=each-commit WORKLOG_GIT_TRACK=false $HOOKS_DIR/auto-commit.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"block"* ]]
  ! echo "$output" | grep -q "포함"
}

@test "auto-commit: TIMING=session-end + no worklog file - block for worklog" {
  echo "change" > "$TEST_DIR/test.txt"
  git add test.txt
  INPUT='{"cwd":"'"$TEST_DIR"'","stop_hook_active":false}'
  run bash -c "echo '$INPUT' | COMMIT_TIMING=session-end WORKLOG_TIMING=session-end $HOOKS_DIR/auto-commit.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"block"* ]]
  [[ "$output" == *"/worklog"* ]]
}

@test "auto-commit: TIMING=session-end + worklog exists - no worklog block" {
  mkdir -p "$TEST_DIR/.worklogs"
  echo "# worklog" > "$TEST_DIR/.worklogs/$(date +%Y-%m-%d).md"
  INPUT='{"cwd":"'"$TEST_DIR"'","stop_hook_active":false}'
  run bash -c "echo '$INPUT' | COMMIT_TIMING=session-end WORKLOG_TIMING=session-end $HOOKS_DIR/auto-commit.sh"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "auto-commit: stop_hook_active=true - skip (reentry guard)" {
  echo "hello" > "$TEST_DIR/test.txt"
  git add test.txt
  INPUT='{"cwd":"'"$TEST_DIR"'","stop_hook_active":true}'
  run bash -c "echo '$INPUT' | COMMIT_TIMING=session-end $HOOKS_DIR/auto-commit.sh"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "auto-commit: only .worklogs/ changes - no block" {
  mkdir -p "$TEST_DIR/.worklogs"
  echo "log" > "$TEST_DIR/.worklogs/2026-03-01.md"
  INPUT='{"cwd":"'"$TEST_DIR"'","stop_hook_active":false}'
  run bash -c "echo '$INPUT' | COMMIT_TIMING=session-end WORKLOG_TIMING=each-commit $HOOKS_DIR/auto-commit.sh"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- worklog.sh (PostToolUse collector) ---

@test "worklog: TIMING=each-commit - collects JSONL" {
  INPUT='{"session_id":"bats-test-ec","tool_name":"Bash","tool_input":{"command":"ls"}}'
  run bash -c "echo '$INPUT' | WORKLOG_TIMING=each-commit $HOOKS_DIR/worklog.sh"
  [ "$status" -eq 0 ]
  [ -f "$HOME/.claude/worklogs/.collecting/bats-test-ec.jsonl" ]
  rm -f "$HOME/.claude/worklogs/.collecting/bats-test-ec.jsonl"
}

@test "worklog: TIMING=session-end - collects JSONL" {
  INPUT='{"session_id":"bats-test-se","tool_name":"Read","tool_input":{}}'
  run bash -c "echo '$INPUT' | WORKLOG_TIMING=session-end $HOOKS_DIR/worklog.sh"
  [ "$status" -eq 0 ]
  [ -f "$HOME/.claude/worklogs/.collecting/bats-test-se.jsonl" ]
  rm -f "$HOME/.claude/worklogs/.collecting/bats-test-se.jsonl"
}

@test "worklog: TIMING=manual - skips JSONL collection" {
  INPUT='{"session_id":"bats-test-manual","tool_name":"Bash","tool_input":{"command":"ls"}}'
  run bash -c "echo '$INPUT' | WORKLOG_TIMING=manual $HOOKS_DIR/worklog.sh"
  [ "$status" -eq 0 ]
  [ ! -f "$HOME/.claude/worklogs/.collecting/bats-test-manual.jsonl" ]
}

# --- notion-worklog.sh ---
# Note: script auto-sources ~/.claude/.env, so we override with explicit env vars

@test "notion-worklog: missing NOTION_TOKEN (no .env) - fails with error" {
  # Temporarily rename .env to prevent auto-sourcing
  [ -f "$HOME/.claude/.env" ] && mv "$HOME/.claude/.env" "$HOME/.claude/.env.bak"
  run bash -c "NOTION_TOKEN='' NOTION_DB_ID='' bash $HOME/.claude/scripts/notion-worklog.sh 'title' '2026-03-01' 'proj' 100 0.5 1 'content'"
  [ -f "$HOME/.claude/.env.bak" ] && mv "$HOME/.claude/.env.bak" "$HOME/.claude/.env"
  [ "$status" -ne 0 ]
  [[ "$output" == *"NOTION_TOKEN"* ]]
}

@test "notion-worklog: missing NOTION_DB_ID - fails with specific error" {
  run bash -c "NOTION_TOKEN='fake_token' NOTION_DB_ID='' bash $HOME/.claude/scripts/notion-worklog.sh 'title' '2026-03-01' 'proj' 100 0.5 1 'content'"
  [ "$status" -ne 0 ]
  [[ "$output" == *"NOTION_DB_ID"* ]]
}

@test "notion-worklog: auto-sources .env for NOTION_TOKEN" {
  # Script should load token from .env even without explicit env var
  run bash -c "NOTION_DB_ID='' bash $HOME/.claude/scripts/notion-worklog.sh 'title' '2026-03-01' 'proj' 100 0.5 1 'content'"
  [ "$status" -ne 0 ]
  # Should fail on DB_ID (not TOKEN), proving .env was loaded
  [[ "$output" == *"NOTION_DB_ID"* ]]
}
