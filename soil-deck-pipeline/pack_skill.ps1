# pack_skill.ps1 (ASCII only) - zip a skill folder into <name>.skill
# Uses System.IO.Compression with forward-slash entry names so the
# claude.ai upload UI accepts it (Compress-Archive writes backslashes -> rejected).
param(
    [string]$SkillDir = "C:\Users\User\claude-skills\soil-deck-pipeline",
    [string]$OutFile  = "C:\Users\User\claude-skills\soil-deck-pipeline.skill"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = (Get-Item -LiteralPath $SkillDir).Name   # entry prefix, e.g. soil-deck-pipeline
if (Test-Path -LiteralPath $OutFile) { Remove-Item -LiteralPath $OutFile -Force }

$fs = [System.IO.File]::Open($OutFile, [System.IO.FileMode]::CreateNew)
$zip = New-Object System.IO.Compression.ZipArchive($fs, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    $base = (Resolve-Path -LiteralPath $SkillDir).Path
    $files = Get-ChildItem -LiteralPath $SkillDir -Recurse -File |
             Where-Object { $_.Name -ne "pack_skill.ps1" }   # don't ship the packer
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($base.Length).TrimStart('\')
        $entryName = "$root/" + ($rel -replace '\\', '/')      # force forward slashes
        $entry = $zip.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
        $in = [System.IO.File]::OpenRead($f.FullName)
        $out = $entry.Open()
        try { $in.CopyTo($out) } finally { $out.Dispose(); $in.Dispose() }
        Write-Host "  + $entryName"
    }
} finally {
    $zip.Dispose(); $fs.Dispose()
}
$kb = [int]((Get-Item -LiteralPath $OutFile).Length / 1KB)
Write-Host "[OK] $OutFile ($kb KB)"
