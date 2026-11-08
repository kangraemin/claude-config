import XCTest
// 화면을 덮은 iOS 시스템 알림(Apple 계정 로그인 등)을 springboard에서 '취소/나중에/닫기'로 닫는다
final class KillTests: XCTestCase {
  func testDismiss() {
    let sb = XCUIApplication(bundleIdentifier: "com.apple.springboard")
    let names = ["취소", "나중에 다시 알림", "나중에", "닫기", "Cancel", "Not Now", "Later", "확인"]
    var closed = 0
    for _ in 0..<6 {
      var hit = false
      for alert in sb.alerts.allElementsBoundByIndex {
        print("ALERT:", alert.label)
        for n in names where alert.buttons[n].exists { alert.buttons[n].tap(); hit = true; closed += 1; print("TAPPED:", n); break }
        if hit { break }
      }
      if !hit {
        for n in names.prefix(7) where sb.buttons[n].exists && sb.buttons[n].isHittable { sb.buttons[n].tap(); hit = true; closed += 1; print("TAPPED btn:", n); break }
      }
      if !hit { break }
      sleep(2)
    }
    print("CLOSED", closed)
  }
}
