"""結構檢查（不編譯）：ios/Voice2Txt 下每個 .swift 都在 project.pbxproj 的
PBXFileReference 與 PBXBuildFile 中，且 iPad/iPhone 方向 key 與 TARGETED_DEVICE_FAMILY '1,2' 存在。
結果寫入 verification/ios-project-structure-2026-11-13.json。這不代表 App 可編譯。"""
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
pbx = (root / 'ios' / 'Voice2Txt.xcodeproj' / 'project.pbxproj').read_text(encoding='utf-8')
swift_files = sorted(p.name for p in (root / 'ios' / 'Voice2Txt').glob('*.swift'))

# 以 PBXFileReference 的 path 找出 id，再確認有 PBXBuildFile 的 fileRef 指向它，且該 build file 在 Sources phase。
sources_phase = re.search(r'"isa" = "PBXSourcesBuildPhase";.*?"files" = \((.*?)\)', pbx, re.S)
phase_files = set(re.findall(r'"([0-9A-F]{24})"', sources_phase.group(1))) if sources_phase else set()
files = {}
for name in swift_files:
    ref = re.search(r'"([0-9A-F]{24})" = \{\s*"isa" = "PBXFileReference";[^}]*?"path" = "%s";' % re.escape(name), pbx, re.S)
    build = None
    if ref:
        build = re.search(r'"([0-9A-F]{24})" = \{\s*"isa" = "PBXBuildFile";\s*"fileRef" = "%s";' % ref.group(1), pbx, re.S)
    files[name] = {
        'PBXFileReference': bool(ref),
        'PBXBuildFile': bool(build),
        'in_sources_build_phase': bool(build and build.group(1) in phase_files),
    }

iphone_key = 'INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone'
ipad_key = 'INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad'
family = len(re.findall(r'"TARGETED_DEVICE_FAMILY" = "1,2";', pbx))
checks = {
    'every_swift_in_pbxproj': all(all(v.values()) for v in files.values()) and bool(files),
    'orientation_ipad_key': ipad_key in pbx,
    'orientation_iphone_key': iphone_key in pbx,
    'targeted_device_family_1_2': family >= 1,
}
report = {
    'task': 'T03',
    'note': '結構檢查，未編譯；不代表 App 可在 Xcode 建置。',
    'swift_files': files,
    'targeted_device_family_1_2_count': family,
    'checks': checks,
    'ok': all(checks.values()),
}
out = root / 'verification' / 'ios-project-structure-2026-11-13.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if report['ok'] else 1)
