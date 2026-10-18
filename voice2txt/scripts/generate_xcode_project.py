"""建立可直接用 Xcode 開啟的專案；不依賴 XcodeGen 或第三方套件。"""
from pathlib import Path


def identifier(number):
    return f'{number:024X}'


objects = {}


def add(number, kind, **fields):
    objects[identifier(number)] = dict(isa=kind, **fields)
    return identifier(number)


sources = ['Voice2TxtApp.swift', 'ContentView.swift', 'Transcriber.swift', 'AudioChunker.swift']
for offset, filename in enumerate(sources):
    add(20 + offset, 'PBXFileReference', lastKnownFileType='sourcecode.swift', path=filename, sourceTree='<group>')
    add(30 + offset, 'PBXBuildFile', fileRef=identifier(20 + offset))
add(40, 'PBXFileReference', explicitFileType='wrapper.application', includeInIndex='0', path='Voice2Txt.app', sourceTree='BUILT_PRODUCTS_DIR')
add(2, 'PBXGroup', children=[identifier(3), identifier(4)], sourceTree='<group>')
add(3, 'PBXGroup', path='Voice2Txt', children=[identifier(20 + i) for i in range(len(sources))], sourceTree='<group>')
add(4, 'PBXGroup', name='Products', children=[identifier(40)], sourceTree='<group>')
add(10, 'PBXSourcesBuildPhase', buildActionMask='2147483647', files=[identifier(30 + i) for i in range(len(sources))], runOnlyForDeploymentPostprocessing='0')
add(11, 'PBXFrameworksBuildPhase', buildActionMask='2147483647', files=[identifier(51)], runOnlyForDeploymentPostprocessing='0')
add(12, 'PBXResourcesBuildPhase', buildActionMask='2147483647', files=[], runOnlyForDeploymentPostprocessing='0')
add(50, 'XCRemoteSwiftPackageReference', repositoryURL='https://github.com/argmaxinc/WhisperKit.git', requirement={'kind': 'exactVersion', 'version': '0.9.4'})
add(52, 'XCSwiftPackageProductDependency', package=identifier(50), productName='WhisperKit')
add(51, 'PBXBuildFile', productRef=identifier(52))
add(5, 'PBXNativeTarget', buildConfigurationList=identifier(61), buildPhases=[identifier(10), identifier(11), identifier(12)], buildRules=[], dependencies=[], name='Voice2Txt', packageProductDependencies=[identifier(52)], productName='Voice2Txt', productReference=identifier(40), productType='com.apple.product-type.application')
add(1, 'PBXProject', attributes={'BuildIndependentTargetsInParallel': '1', 'LastUpgradeCheck': '1600'}, buildConfigurationList=identifier(60), compatibilityVersion='Xcode 14.0', developmentRegion='zh_TW', knownRegions=['zh_TW', 'en', 'Base'], mainGroup=identifier(2), packageReferences=[identifier(50)], productRefGroup=identifier(4), projectDirPath='', projectRoot='', targets=[identifier(5)])
for number, name in [(70, 'Debug'), (71, 'Release')]:
    add(number, 'XCBuildConfiguration', name=name, buildSettings={'SDKROOT': 'iphoneos', 'IPHONEOS_DEPLOYMENT_TARGET': '16.0', 'CLANG_ENABLE_MODULES': 'YES', 'SWIFT_VERSION': '5.0', 'SWIFT_OPTIMIZATION_LEVEL': '-Onone' if name == 'Debug' else '-O'})
for number, name in [(72, 'Debug'), (73, 'Release')]:
    add(number, 'XCBuildConfiguration', name=name, buildSettings={
        'CODE_SIGN_STYLE': 'Automatic', 'CURRENT_PROJECT_VERSION': '1',
        'MARKETING_VERSION': '0.1.0', 'GENERATE_INFOPLIST_FILE': 'YES',
        'INFOPLIST_KEY_CFBundleDisplayName': 'Voice2Txt',
        'INFOPLIST_KEY_NSMicrophoneUsageDescription': '使用麥克風進行本機語音轉錄及中英翻譯。',
        'INFOPLIST_KEY_UILaunchScreen_Generation': 'YES',
        'INFOPLIST_KEY_UIApplicationSceneManifest_Generation': 'YES',
        'PRODUCT_BUNDLE_IDENTIFIER': 'org.voice2txt.app',
        'PRODUCT_NAME': '$(TARGET_NAME)', 'TARGETED_DEVICE_FAMILY': '1,2',
        'SUPPORTED_PLATFORMS': 'iphoneos iphonesimulator',
        'SWIFT_EMIT_LOC_STRINGS': 'YES',
    })
add(60, 'XCConfigurationList', buildConfigurations=[identifier(70), identifier(71)], defaultConfigurationIsVisible='0', defaultConfigurationName='Release')
add(61, 'XCConfigurationList', buildConfigurations=[identifier(72), identifier(73)], defaultConfigurationIsVisible='0', defaultConfigurationName='Release')


def serialize(value, depth=0):
    if isinstance(value, dict):
        lines = [f'{serialize(key)} = {serialize(item, depth + 1)};' for key, item in value.items()]
        return '{\n' + '\n'.join('\t' * (depth + 1) + line for line in lines) + '\n' + '\t' * depth + '}'
    if isinstance(value, list):
        return '(' + ', '.join(serialize(item, depth + 1) for item in value) + (',' if value else '') + ')'
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


root = Path(__file__).resolve().parent.parent / 'ios' / 'Voice2Txt.xcodeproj'
root.mkdir(exist_ok=True)
project = dict(archiveVersion='1', classes={}, objectVersion='56', objects=objects, rootObject=identifier(1))
(root / 'project.pbxproj').write_text('// !$*UTF8*$!\n' + serialize(project) + '\n', encoding='utf-8')
print(root)
