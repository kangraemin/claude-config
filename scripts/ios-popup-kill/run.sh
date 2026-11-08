#!/bin/bash
# 실기기 화면을 덮은 iOS 시스템 알림('Apple 계정에 로그인', '소프트웨어 업데이트' 등)을 XCUITest로 '취소/나중에'를 눌러 닫는다.
# LLM 호출 없음 (CLAUDE_P_MAX=0)
# 사용: run.sh [기기 하드웨어 UDID, 기본 Eunmi iPhone 00008101-001E194C3481001E]
# 전제: 프로필 popupkiller-dev(ASC 와일드카드 com.oguriworks.popupkiller.*, 2026-11-08 생성), 인증서 FE2F2AC2...
# 폰 암호가 필요한 상태면 "Timed out while enabling automation mode"로 실패 → 사용자에게 암호 한 번만 요청. 재부팅 금지.
# 출력: ALERT:<제목> / TAPPED:<버튼> / CLOSED <개수>
# 검증 2026-11-08: Eunmi iPhone(iOS 26.3)에서 '소프트웨어 업데이트' → '나중에' 닫힘.
set -e
U=${1:-00008101-001E194C3481001E}
SRC="$(cd "$(dirname "$0")" && pwd)"
D=${TMPDIR:-/tmp}/ios-popup-kill
mkdir -p "$D"
cp -R "$SRC/Host" "$SRC/UIT" "$SRC/project.yml" "$D/"
cd "$D"
[ -d PopupKiller.xcodeproj ] || xcodegen generate >/dev/null
xcodebuild build-for-testing -project PopupKiller.xcodeproj -scheme UIT -destination "id=$U" -derivedDataPath dd \
  CODE_SIGN_IDENTITY=FE2F2AC2E01EBCBD0355FC4359F496192541FA69 -quiet 2>&1 | grep -i " error" || true
timeout 200 xcodebuild test-without-building -xctestrun dd/Build/Products/*.xctestrun -destination "id=$U" 2>&1 \
  | grep -E "ALERT|TAPPED|CLOSED|Timed out|failed"
