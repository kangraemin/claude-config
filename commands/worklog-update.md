---
description: worklog-for-claude 최신 버전 확인 및 업데이트
---

# /update-worklog

아래 코드를 그대로 실행한다. 경로나 파일명을 변경하지 않는다.

## Step 1: 버전 확인

```bash
bash "$HOME/.claude/scripts/worklog-update-check.sh" --check-only
```

## Step 2: 결과 처리

- `status: up-to-date` → "최신 버전입니다 (SHA)" 출력 후 종료
- `status: update-available` → 사용자에게 업데이트 여부 확인

## Step 3: 업데이트 실행 (사용자 승인 시)

```bash
bash "$HOME/.claude/scripts/worklog-update-check.sh" --force
```
