# =====================================================================
# sync_to_pages.ps1  -  One-click: copy a built HTML deck into a
#                       GitHub Pages repo and commit + push (only if changed).
#
# ASCII-only on purpose. Chinese commit message lives in a UTF-8 sidecar
# file passed via -MsgTemplate (with a {STAMP} placeholder), read with an
# explicit UTF-8 decoder. See windows-build-pitfalls.md pitfall #2 & #9.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File sync_to_pages.ps1 `
#       -SrcHtml "C:\proj\deck.html" `
#       -RepoDir "C:\Users\me\repo" `
#       -RelPath "slides/deck.html" `
#       [-MsgTemplate "C:\proj\commit_msg.txt"] `
#       [-BuildCmd 'python build_html.py'] [-BuildDir 'C:\proj']
# =====================================================================
param(
    [Parameter(Mandatory=$true)][string]$SrcHtml,
    [Parameter(Mandatory=$true)][string]$RepoDir,
    [Parameter(Mandatory=$true)][string]$RelPath,    # path inside repo, forward slashes
    [string]$MsgTemplate = "",
    [string]$BuildCmd = "",
    [string]$BuildDir = ""
)
$ErrorActionPreference = "Stop"
function Step($m){ Write-Host "==> $m" -ForegroundColor Cyan }
function Ok($m){ Write-Host "    $m" -ForegroundColor Green }
function Warn($m){ Write-Host "    $m" -ForegroundColor Yellow }

# 1. Optional rebuild
if ($BuildCmd -ne "") {
    Step "Rebuild: $BuildCmd"
    if ($BuildDir -ne "") { Push-Location $BuildDir } else { Push-Location (Split-Path -Parent $SrcHtml) }
    try {
        Invoke-Expression $BuildCmd
        if ($LASTEXITCODE -ne 0) { throw "build failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
    Ok "Rebuilt."
}

if (-not (Test-Path -LiteralPath $SrcHtml)) { throw "Source not found: $SrcHtml" }

# 2. Copy into repo
Step "Copy into repo"
$dst = Join-Path $RepoDir ($RelPath -replace '/', '\')
$dstDir = Split-Path -Parent $dst
if (-not (Test-Path -LiteralPath $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
Copy-Item -LiteralPath $SrcHtml -Destination $dst -Force
$kb = [int]((Get-Item -LiteralPath $dst).Length / 1KB)
Ok "Copied -> $RelPath ($kb KB)"

# 3. Stage + detect change
Step "Check for changes"
Push-Location $RepoDir
try {
    & git add -- $RelPath | Out-Null
    & git diff --cached --quiet -- $RelPath
    if ($LASTEXITCODE -eq 0) { Warn "No changes. Remote already up to date."; return }
    Ok "Change detected."

    # 4. Commit message (UTF-8 sidecar -> temp -> git commit -F)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    if ($MsgTemplate -ne "" -and (Test-Path -LiteralPath $MsgTemplate)) {
        $msg = ([System.IO.File]::ReadAllText($MsgTemplate, [System.Text.Encoding]::UTF8)).Replace("{STAMP}", $stamp)
    } else {
        $msg = "Update published deck ($stamp)"
    }
    $tmp = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($tmp, $msg, (New-Object System.Text.UTF8Encoding($false)))

    $saved = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & git commit -F $tmp | Out-Null
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $saved; throw "git commit failed" }
    Ok "Committed."

    Step "Push origin main"
    & git push origin main 2>&1 | Write-Host
    $code = $LASTEXITCODE; $ErrorActionPreference = $saved
    if ($code -ne 0) { throw "git push failed (exit $code)" }
    Ok "Pushed."
} finally { Pop-Location }
