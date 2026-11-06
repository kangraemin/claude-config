// 그림이 실제로 차지하는 영역(투명 아닌 픽셀 bbox)을 pt로 잰다. LLM 없음.
// usage:
//   swift glyph.swift symbol <SF이름> <글자크기pt> [weight: ultraLight|thin|light|regular|medium|semibold|bold|heavy|black]
//   swift glyph.swift file <이미지경로(pdf/svg/png)> <틀폭pt> <틀높이pt>   (aspect fit 으로 그렸을 때)
// 출력: JSON {"box_w","box_h","glyph_x","glyph_y","glyph_w","glyph_h"} (pt)
import AppKit

let a = CommandLine.arguments
let scale: CGFloat = 8
func weight(_ s: String) -> NSFont.Weight {
    ["ultralight": .ultraLight, "thin": .thin, "light": .light, "regular": .regular, "medium": .medium,
     "semibold": .semibold, "bold": .bold, "heavy": .heavy, "black": .black][s.lowercased()] ?? .regular
}
var img: NSImage
var boxW: CGFloat, boxH: CGFloat
if a[1] == "symbol" {
    let pt = CGFloat(Double(a[3])!)
    let w = a.count > 4 ? weight(a[4]) : .regular
    guard let base = NSImage(systemSymbolName: a[2], accessibilityDescription: nil) else { print("{\"error\":\"no symbol\"}"); exit(1) }
    img = base.withSymbolConfiguration(.init(pointSize: pt, weight: w))!
    boxW = img.size.width; boxH = img.size.height
} else {
    guard let im = NSImage(contentsOfFile: a[2]) else { print("{\"error\":\"cannot load\"}"); exit(1) }
    boxW = CGFloat(Double(a[3])!); boxH = CGFloat(Double(a[4])!)
    img = im
}
let pw = Int(ceil(boxW * scale)), ph = Int(ceil(boxH * scale))
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: pw, pixelsHigh: ph, bitsPerSample: 8, samplesPerPixel: 4,
                           hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
var dst = NSRect(x: 0, y: 0, width: CGFloat(pw), height: CGFloat(ph))
if a[1] != "symbol" {
    let s = min(CGFloat(pw) / img.size.width, CGFloat(ph) / img.size.height)
    let w = img.size.width * s, h = img.size.height * s
    dst = NSRect(x: (CGFloat(pw) - w) / 2, y: (CGFloat(ph) - h) / 2, width: w, height: h)
}
img.draw(in: dst)
NSGraphicsContext.restoreGraphicsState()
var x0 = pw, y0 = ph, x1 = -1, y1 = -1
for y in 0..<ph { for x in 0..<pw {
    if let c = rep.colorAt(x: x, y: y), c.alphaComponent > 0.5 {
        x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
    }
}}
func r(_ v: CGFloat) -> String { String(format: "%.2f", v) }
print("{\"box_w\":\(r(boxW)),\"box_h\":\(r(boxH)),\"glyph_x\":\(r(CGFloat(x0)/scale)),\"glyph_y\":\(r(CGFloat(y0)/scale)),\"glyph_w\":\(r(CGFloat(x1-x0+1)/scale)),\"glyph_h\":\(r(CGFloat(y1-y0+1)/scale))}")
