---
description: 기존 .worklogs MD 파일을 Notion DB로 마이그레이션
---

# /migrate-worklogs

기존 `.worklogs/*.md` 파일을 Notion DB로 마이그레이션한다.

## 플로우

1. 인자 파싱:
   - `--dry-run` : 실제 전송 없이 파싱 결과만 출력 (기본값)
   - `--date YYYY-MM-DD` : 특정 날짜만 처리
   - `--all` : 실제 전송 실행 (dry-run 아님)

2. 워크로그 디렉토리 결정:
   - 현재 프로젝트 루트의 `.worklogs/` 디렉토리 사용
   - 없으면 `~/.claude/.worklogs/` 사용

3. 환경변수 확인 (`--all` 모드에서만):
   - `NOTION_TOKEN` 없으면 에러 출력 후 종료
   - `NOTION_DB_ID` 없으면 에러 출력 후 종료

4. 실행:
   ```bash
   # dry-run (기본)
   bash ~/.claude/scripts/notion-migrate-worklogs.sh --dry-run [--date YYYY-MM-DD] <worklogs_dir>

   # 실제 마이그레이션
   bash ~/.claude/scripts/notion-migrate-worklogs.sh [--date YYYY-MM-DD] <worklogs_dir>
   ```

5. 결과 출력:
   - dry-run: 파싱된 엔트리 목록 출력 후 "실제 전송하려면 `/migrate-worklogs --all` 실행" 안내
   - 실제: 성공/실패 카운트 출력

## 사용 예시

```
/migrate-worklogs              → dry-run (미리보기)
/migrate-worklogs --all        → 전체 마이그레이션
/migrate-worklogs --date 2026-02-23         → 특정 날짜 dry-run
/migrate-worklogs --date 2026-02-23 --all   → 특정 날짜만 전송
```
