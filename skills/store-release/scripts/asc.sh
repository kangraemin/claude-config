#!/bin/bash
# asc(App Store Connect CLI, brew install asc)를 우리 ASC API 키로 실행한다. 키 값은 출력하지 않는다.
#   asc.sh apps list --output table
#   asc.sh validate --app <앱 ID>
set -e
set -a; source ~/.claude/.env >/dev/null 2>&1; set +a
export ASC_PRIVATE_KEY_PATH="${ASC_PRIVATE_KEY_PATH:-$ASC_KEY_FILE}"
command -v asc >/dev/null || brew install asc >/dev/null
exec asc "$@"
