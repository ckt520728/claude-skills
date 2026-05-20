# =====================================================================
# compress_images.ps1  -  Compress PNG/JPG to web JPEG using .NET
#                         System.Drawing (no Pillow needed).
#
# Why: Anaconda Pillow DLL is often broken on Windows; this avoids it.
# ASCII-only on purpose (PowerShell 5.1 misreads UTF-8 scripts as ANSI).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File compress_images.ps1 `
#       -SrcDir "C:\path\in" -DstDir "C:\path\out" -MaxWidth 1280 -Quality 80
#
# Notes:
#   - Keeps aspect ratio, fills transparent PNG onto white background.
#   - If your source dir has CJK characters in the PATH, first copy the
#     files to an ASCII path via the Bash tool (see windows-build-pitfalls.md
#     pitfall #3), then point -SrcDir at the ASCII path.
# =====================================================================
param(
    [Parameter(Mandatory=$true)][string]$SrcDir,
    [Parameter(Mandatory=$true)][string]$DstDir,
    [int]$MaxWidth = 1280,
    [int]$Quality  = 80
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

if (-not (Test-Path -LiteralPath $DstDir)) {
    New-Item -ItemType Directory -Path $DstDir -Force | Out-Null
}

$enc = ([System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
        Where-Object { $_.MimeType -eq "image/jpeg" })
$ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter(
    [System.Drawing.Imaging.Encoder]::Quality, [long]$Quality)

$files = Get-ChildItem -LiteralPath $SrcDir -File |
         Where-Object { $_.Extension -match '\.(png|jpg|jpeg|bmp)$' }

foreach ($f in $files) {
    $bmp = [System.Drawing.Image]::FromFile($f.FullName)
    $w = $bmp.Width; $h = $bmp.Height
    if ($w -gt $MaxWidth) { $nw = $MaxWidth; $nh = [int]($h * $MaxWidth / $w) }
    else { $nw = $w; $nh = $h }
    $rs = New-Object System.Drawing.Bitmap($nw, $nh)
    $g = [System.Drawing.Graphics]::FromImage($rs)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.Clear([System.Drawing.Color]::White)
    $g.DrawImage($bmp, 0, 0, $nw, $nh)
    $outName = [System.IO.Path]::GetFileNameWithoutExtension($f.Name) + ".jpg"
    $outPath = Join-Path $DstDir $outName
    $rs.Save($outPath, $enc, $ep)
    $kb = [int]((Get-Item -LiteralPath $outPath).Length / 1KB)
    Write-Host ("[OK] {0} : {1}x{2} , {3} KB" -f $outName, $nw, $nh, $kb)
    $g.Dispose(); $rs.Dispose(); $bmp.Dispose()
}
Write-Host "Done."
