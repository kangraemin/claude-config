# /commit

`~/.claude/rules/git-rules.md`의 커밋 규칙을 따른다.

1. `git status`로 변경 파일 확인
2. `git diff` + `git diff --cached`로 변경 내용 분석
3. `git log --oneline -5`로 최근 커밋 스타일 확인
4. git-rules.md의 커밋 규칙에 따라 메시지 작성
5. 변경 파일 개별 `git add`
6. **워크로그 생성**: `~/.claude/hooks/generate-worklog.sh`를 호출하여 워크로그를 생성하고 함께 커밋에 포함한다.
   - stdin으로 `{"session_id":"현재세션ID","cwd":"현재경로","transcript_path":"트랜스크립트경로"}` 전달
   - 반환된 파일 경로를 `git add`
7. HEREDOC으로 커밋 실행
8. `git status`로 결과 확인
