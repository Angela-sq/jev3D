import AppKit
import CoreGraphics
import ApplicationServices
import Foundation

func fail(_ s: String) -> Never { fputs(s + "\n", stderr); exit(1) }
func output(_ x: Any) { if let d = try? JSONSerialization.data(withJSONObject: x, options: [.prettyPrinted, .sortedKeys]), let s = String(data:d, encoding:.utf8) { print(s) } }
func windows() -> [[String:Any]] {
 let pids = Set(NSWorkspace.shared.runningApplications.filter { ($0.executableURL?.path ?? "").contains("/minecraft/runtime/") && $0.executableURL?.lastPathComponent == "java" }.map { $0.processIdentifier })
 return (CGWindowListCopyWindowInfo([.optionAll, .excludeDesktopElements], kCGNullWindowID) as? [[String:Any]] ?? []).filter {
  pids.contains(($0[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value ?? -1) &&
  ($0[kCGWindowName as String] as? String ?? "").hasPrefix("Minecraft ") &&
  !($0[kCGWindowName as String] as? String ?? "").contains("Hidden Utility")
 }
}
let args = Array(CommandLine.arguments.dropFirst())
guard let mode = args.first else { fail("Use: status | capture WINDOW_ID OUTPUT.png | key WINDOW_ID KEY MILLISECONDS | look WINDOW_ID DX DY | click WINDOW_ID {left,right} MILLISECONDS") }
if mode == "status" {
 output(["screenRecording": CGPreflightScreenCaptureAccess(), "accessibility": AXIsProcessTrusted(), "windows": windows(), "javaApps": NSWorkspace.shared.runningApplications.filter { ($0.executableURL?.path ?? "").contains("/bin/java") }.map { ["pid": $0.processIdentifier, "name": $0.localizedName ?? "", "executable": $0.executableURL?.path ?? "", "bundle": $0.bundleIdentifier ?? ""] as [String:Any] }]); exit(0)
}

let keys: [String:CGKeyCode] = ["w":13,"a":0,"s":1,"d":2,"space":49,"escape":53,"e":14,"1":18,"2":19,"shift":56]
switch mode {
case "capture": guard args.count == 3 else { fail("capture WINDOW_ID OUTPUT.png") }
case "key": guard args.count == 4, keys[args[2]] != nil, let ms = Int(args[3]), (0...1000).contains(ms) else { fail("Invalid key or duration; maximum 1000 ms") }
case "look": guard args.count == 4, let dx = Int64(args[2]), let dy = Int64(args[3]), (-200...200).contains(dx), (-200...200).contains(dy) else { fail("Invalid mouse delta; each must be -200..200") }
case "click": guard args.count == 4, ["left","right"].contains(args[2]), let ms = Int(args[3]), (0...1000).contains(ms) else { fail("Invalid click or duration; maximum 1000 ms") }
default: fail("Unknown mode")
}

guard args.count >= 2, let id = UInt32(args[1]), let win = windows().first(where: { ($0[kCGWindowNumber as String] as? NSNumber)?.uint32Value == id }), let pid = (win[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value else { fail("Target must be a Minecraft game window from status") }
if mode == "capture" {
 guard args.count == 3 else { fail("capture WINDOW_ID OUTPUT.png") }
 guard CGPreflightScreenCaptureAccess() else { fail("Screen Recording permission is not available to this helper") }
 let p = Process(); p.executableURL = URL(fileURLWithPath:"/usr/sbin/screencapture"); p.arguments = ["-x", "-o", "-l", String(id), args[2]]
 try p.run(); p.waitUntilExit(); guard p.terminationStatus == 0 else { fail("Capture failed") }; output(["window":id,"path":args[2],"capturedAt":Date().timeIntervalSince1970]); exit(0)
}
guard AXIsProcessTrusted() else { fail("Accessibility permission is not available to this helper") }
guard let target = NSRunningApplication(processIdentifier:pid) else { fail("Game exited") }
target.unhide()
let appAX = AXUIElementCreateApplication(pid)
_ = AXUIElementSetAttributeValue(appAX, kAXFrontmostAttribute as CFString, kCFBooleanTrue)
var axWindows: CFTypeRef?
if AXUIElementCopyAttributeValue(appAX, kAXWindowsAttribute as CFString, &axWindows) == .success, let ws = axWindows as? [AXUIElement] {
 for w in ws {
  var title: CFTypeRef?
  AXUIElementCopyAttributeValue(w, kAXTitleAttribute as CFString, &title)
  if (title as? String) == (win[kCGWindowName as String] as? String) {
   AXUIElementSetAttributeValue(w, kAXMinimizedAttribute as CFString, kCFBooleanFalse)
   AXUIElementPerformAction(w, kAXRaiseAction as CFString)
  }
 }
}
guard target.activate(options: []) else { fail("Could not focus Minecraft") }
for _ in 0..<20 { if NSWorkspace.shared.frontmostApplication?.processIdentifier == pid { break }; RunLoop.current.run(until:Date().addingTimeInterval(0.1)) }
guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else { fail("Minecraft is not foreground; refusing input") }
let source = CGEventSource(stateID: .hidSystemState)
let start = Date().timeIntervalSince1970
if mode == "key" {
 let keys: [String:CGKeyCode] = ["w":13,"a":0,"s":1,"d":2,"space":49,"escape":53,"e":14,"1":18,"2":19,"shift":56]
 guard args.count == 4, let code = keys[args[2]], let ms = Int(args[3]), ms >= 0, ms <= 1000 else { fail("key WINDOW_ID {w,a,s,d,space,escape,e,1,2,shift} MILLISECONDS (0..1000)") }
 guard let down = CGEvent(keyboardEventSource:source, virtualKey:code, keyDown:true), let up = CGEvent(keyboardEventSource:source, virtualKey:code, keyDown:false) else { fail("Cannot create events") }
 down.postToPid(pid)
 Thread.sleep(forTimeInterval:Double(ms)/1000)
 up.postToPid(pid)
} else if mode == "look" {
 guard args.count == 4, let dx = Int64(args[2]), let dy = Int64(args[3]), (-200...200).contains(dx), (-200...200).contains(dy) else { fail("look WINDOW_ID DX DY (each -200..200)") }
 guard let event = CGEvent(source:source) else { fail("Cannot read mouse position") }
 guard let move = CGEvent(mouseEventSource:source, mouseType:.mouseMoved, mouseCursorPosition:CGPoint(x:event.location.x + CGFloat(dx), y:event.location.y + CGFloat(dy)), mouseButton:.left) else { fail("Cannot create mouse event") }
 move.setIntegerValueField(.mouseEventDeltaX, value:dx); move.setIntegerValueField(.mouseEventDeltaY, value:dy); move.post(tap:.cghidEventTap)
} else if mode == "click" {
 let button: CGMouseButton = args[2] == "left" ? .left : .right
 let downType: CGEventType = button == .left ? .leftMouseDown : .rightMouseDown
 let upType: CGEventType = button == .left ? .leftMouseUp : .rightMouseUp
 guard let bounds = win[kCGWindowBounds as String] as? [String:Double], let x = bounds["X"], let y = bounds["Y"], let width = bounds["Width"], let height = bounds["Height"] else { fail("Missing window bounds") }
 let point = CGPoint(x:x + width/2, y:y + height/2)
 guard let down = CGEvent(mouseEventSource:source, mouseType:downType, mouseCursorPosition:point, mouseButton:button), let up = CGEvent(mouseEventSource:source, mouseType:upType, mouseCursorPosition:point, mouseButton:button) else { fail("Cannot create mouse events") }
 for event in [down, up] {
  event.setIntegerValueField(.mouseEventClickState, value:1)
  event.setIntegerValueField(.mouseEventWindowUnderMousePointer, value:Int64(id))
  event.setIntegerValueField(.mouseEventWindowUnderMousePointerThatCanHandleThisEvent, value:Int64(id))
 }
 down.post(tap:.cghidEventTap)
 Thread.sleep(forTimeInterval:Double(Int(args[3])!)/1000)
 up.post(tap:.cghidEventTap)
} else { fail("Unknown mode") }
output(["window":id,"operation":mode,"action":Array(args.dropFirst(2)),"startedAt":start,"finishedAt":Date().timeIntervalSince1970])
