#!/bin/bash
# stdin/-c 로 넘긴 파이썬에서 multiprocessing을 쓰면 macOS spawn 워커가 무한 재생성되며 디스크를 채운다.
# 두 번 사고(10/09 14GB, 10/22 3GB)가 나서 글 규칙 대신 실행 전에 막는다.
cmd=$(jq -r '.tool_input.command // empty')
echo "$cmd" | grep -Eq 'python3?(\.[0-9]+)?( -[A-Za-z]+)* (-|-c)( |$|<)' || exit 0
echo "$cmd" | grep -Eq 'multiprocessing|ProcessPool|Pool\(|joblib|concurrent\.futures' || exit 0
echo "차단: stdin/-c 파이썬에서 multiprocessing을 쓰면 macOS spawn 워커가 '<stdin>'을 못 찾고 무한 재생성된다. 스크립트를 .py 파일로 저장하고 if __name__ == '__main__': 가드와 timeout을 붙여 실행하라." >&2
exit 2
