param([switch]$IncludeGpu)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$voice2txtBuildArgs = @('-m','PyInstaller','--noconfirm','--onedir','--windowed','--name','Voice2Txt','--collect-all','opencc','--collect-all','faster_whisper','--collect-all','ctranslate2','--exclude-module','torch','--exclude-module','tensorflow','--exclude-module','matplotlib','--exclude-module','pandas','--exclude-module','scipy','--exclude-module','IPython','--add-data','models\whisper-small;models\whisper-small')
if ($IncludeGpu) {
    $voice2txtBuildArgs += @('--add-data','gpu\nvidia;gpu\nvidia')
    foreach ($voice2txtSize in @('medium','large-v3')) {
        if (Test-Path -LiteralPath "models\whisper-$voice2txtSize\model.bin") {
            $voice2txtBuildArgs += @('--add-data',"models\whisper-$voice2txtSize;models\whisper-$voice2txtSize")
        }
    }
}
$voice2txtBuildArgs += 'run_desktop.py'
& '.\.build-venv\Scripts\python.exe' @voice2txtBuildArgs
if ($LASTEXITCODE -ne 0) { throw 'Windows 建置失敗' }
# Anaconda 可能帶入舊版 14.27 Runtime，CTranslate2 載入模型時會崩潰。
# 使用已安裝、版本較新的 x64 Visual C++ Runtime；只更新產物中的副本。
foreach ($voice2txtRuntimeName in @('msvcp140.dll','msvcp140_1.dll','vcruntime140.dll','vcruntime140_1.dll')) {
    $voice2txtRuntimeSource = Join-Path "$env:WINDIR\System32" $voice2txtRuntimeName
    $voice2txtRuntimeDestination = Join-Path 'dist\Voice2Txt\_internal' $voice2txtRuntimeName
    if (-not (Test-Path -LiteralPath $voice2txtRuntimeSource)) { throw "缺少新版 Visual C++ Runtime：$voice2txtRuntimeName" }
    Copy-Item -LiteralPath $voice2txtRuntimeSource -Destination $voice2txtRuntimeDestination -Force
}
& '.\.build-venv\Scripts\python.exe' 'scripts\collect_licenses.py'
Copy-Item -LiteralPath 'README.md' -Destination 'dist\Voice2Txt\使用說明.md' -Force
Copy-Item -LiteralPath 'USER_MANUAL.md' -Destination 'dist\Voice2Txt\使用者手冊.md' -Force
