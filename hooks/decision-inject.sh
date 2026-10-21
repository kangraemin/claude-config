#!/bin/bash
# decision-inject: SessionStart hook. 본체는 decision_inject.py (2026-10-22: 8KB 상한·0.3초로 재작성).
exec python3 "$(dirname "$0")/decision_inject.py"
