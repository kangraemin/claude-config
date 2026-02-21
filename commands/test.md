# /test — 프로젝트 테스트 실행

프로젝트 타입을 자동 감지하여 적절한 테스트 명령어를 실행한다.

1. 프로젝트 타입 감지:
   - `Package.swift` 존재 → `swift test`
   - `*.xcodeproj` 또는 `*.xcworkspace` 존재 → `xcodebuild test`
   - `package.json` 존재 → `npm test` 또는 `yarn test`
   - `build.gradle` 존재 → `./gradlew test`
   - `Cargo.toml` 존재 → `cargo test`
   - `go.mod` 존재 → `go test ./...`
   - `pytest.ini` 또는 `setup.py` 존재 → `pytest`

2. 테스트 실행

3. 결과 요약 보고:
   - 총 테스트 수
   - 성공 / 실패 / 스킵 수
   - 실패한 테스트가 있으면 실패 내용 상세 출력
