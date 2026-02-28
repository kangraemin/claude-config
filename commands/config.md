---
description: Claude Code 설정 조회 및 변경
---

# /config

Claude Code 설정(플래그)을 조회하거나 변경한다.

## 사용법

- `/config` — 현재 설정 조회 (글로벌 + 로컬)
- `/config set KEY=VALUE` — 글로벌 설정 변경
- `/config set KEY=VALUE --local` — 현재 프로젝트 로컬 설정 변경
- `/config reset KEY` — 로컬에서 해당 키 제거 (글로벌 값으로 복원)
- `/config setup` — 대화형 마법사 실행 (`bash ~/.claude/scripts/setup.sh`)
- `/config setup --local` — 현재 프로젝트 대화형 마법사 실행

## 지원 키

| 키 | 가능한 값 | 설명 |
|---|---|---|
| `model` | opusplan / claude-sonnet-4-6 / claude-haiku-4-5-20251001 | 사용 모델 |
| `WORKLOG_TIMING` | each-commit / session-end / manual | 워크로그 작성 시점 |
| `COMMIT_TIMING` | session-end / manual | 커밋 트리거 시점 |
| `COMMIT_LANG` | ko / en | 커밋 메시지 언어 |
| `ENABLE_TOOL_SEARCH` | true / false | 도구 검색 활성화 |

## 동작 규칙

### 조회 (`/config`)
1. `~/.claude/settings.json` (글로벌) 읽기
2. `<cwd>/.claude/settings.json` (로컬) 있으면 함께 읽기
3. 키별로 어디서 오는지(글로벌/로컬) 표시
4. 로컬 값이 글로벌을 오버라이드함을 명시

### 변경 (`/config set`)
- `--local` 없으면 `~/.claude/settings.json` 수정
- `--local` 있으면 `<cwd>/.claude/settings.json` 수정 (없으면 생성)
- `model` 키: `.model` 경로에 저장
- 나머지 키: `.env.KEY` 경로에 저장
- `jq`로 수정, 기존 값 보존

### 제거 (`/config reset KEY`)
- `<cwd>/.claude/settings.json`에서 해당 키 제거
- 글로벌 값으로 복원됨을 안내

### 마법사 (`/config setup`)
```bash
bash ~/.claude/scripts/setup.sh
# 로컬:
bash ~/.claude/scripts/setup.sh --local
```

## jq 수정 예시

```bash
# 글로벌 WORKLOG_MODE=off
jq '.env.WORKLOG_MODE = "off"' ~/.claude/settings.json > /tmp/s.json && mv /tmp/s.json ~/.claude/settings.json

# 로컬 COMMIT_LANG=en
mkdir -p .claude
[[ -f .claude/settings.json ]] || echo '{}' > .claude/settings.json
jq '.env.COMMIT_LANG = "en"' .claude/settings.json > /tmp/s.json && mv /tmp/s.json .claude/settings.json

# 로컬 키 제거
jq 'del(.env.COMMIT_LANG)' .claude/settings.json > /tmp/s.json && mv /tmp/s.json .claude/settings.json
```
