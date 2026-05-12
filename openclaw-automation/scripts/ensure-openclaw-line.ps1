param(
  [string]$OpenClawHome = "$env:USERPROFILE\.openclaw",
  [string]$NodeExe = "C:\Program Files\nodejs\node.exe",
  [string]$NpxCmd = "npx.cmd",
  [int]$ProxyPort = 18790,
  [int]$GatewayPort = 18789,
  [string]$LogDir = "C:\Temp",
  [string]$ProxyTaskName = "OpenClawLineWebhookProxy",
  [string]$TunnelTaskName = "OpenClawLineCloudflaredTunnel",
  [string]$RecoveryTaskName = "OpenClawLineEnsureDaily",
  [switch]$RegisterStartupRecovery
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
  Write-Host "[openclaw-line] $Message"
}

function Require-File($Path, $Label) {
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Missing $Label at $Path"
  }
}

function Wait-HttpOk($Uri, $Seconds) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    try {
      $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 5
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
        return $true
      }
    } catch {
      Start-Sleep -Seconds 1
    }
  } while ((Get-Date) -lt $deadline)
  return $false
}

function Register-Task($TaskName, $Execute, $Argument) {
  $action = New-ScheduledTaskAction -Execute $Execute -Argument $Argument
  $task = New-ScheduledTask -Action $action
  Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
  Start-ScheduledTask -TaskName $TaskName
}

function Get-TunnelUrl($LogPath) {
  if (-not (Test-Path -LiteralPath $LogPath)) {
    return $null
  }
  $content = Get-Content -LiteralPath $LogPath -Raw
  $match = [regex]::Match($content, "https://[a-z0-9-]+\.trycloudflare\.com")
  if ($match.Success) {
    return $match.Value
  }
  return $null
}

function Invoke-NodeLineApi($ConfigPath, $Endpoint) {
  $script = @"
const fs = require("fs");
const rawConfig = fs.readFileSync(process.argv[2], "utf8").replace(/^\uFEFF/, "");
const cfg = JSON.parse(rawConfig);
const endpoint = process.argv[3];
const token = cfg.channels && cfg.channels.line && cfg.channels.line.channelAccessToken;
if (!token) {
  throw new Error("Missing channels.line.channelAccessToken in OpenClaw config");
}
async function main() {
  const update = await fetch("https://api.line.me/v2/bot/channel/webhook/endpoint", {
    method: "PUT",
    headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint }),
  });
  const updateText = await update.text();
  console.log("LINE endpoint update:", update.status, updateText);
  if (!update.ok) process.exit(2);
  const test = await fetch("https://api.line.me/v2/bot/channel/webhook/test", {
    method: "POST",
    headers: { Authorization: "Bearer " + token },
  });
  const testText = await test.text();
  console.log("LINE webhook test:", test.status, testText);
  if (!test.ok || !testText.includes('"success":true')) process.exit(3);
}
main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
"@
  $tempScript = Join-Path $env:TEMP "openclaw-line-api-update.js"
  Set-Content -LiteralPath $tempScript -Value $script -Encoding UTF8
  & $NodeExe $tempScript $ConfigPath $Endpoint
  if ($LASTEXITCODE -ne 0) {
    throw "LINE API update/test failed with exit code $LASTEXITCODE"
  }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$proxyScript = Join-Path $scriptRoot "line-webhook-proxy.mjs"
$configPath = Join-Path $OpenClawHome "openclaw.json"
$proxyOut = Join-Path $LogDir "line-webhook-proxy.out.log"
$proxyErr = Join-Path $LogDir "line-webhook-proxy.err.log"
$tunnelOut = Join-Path $LogDir "cloudflared-openclaw.out.log"
$tunnelErr = Join-Path $LogDir "cloudflared-openclaw.err.log"

Require-File $NodeExe "Node.js executable"
Require-File $proxyScript "LINE webhook proxy script"
Require-File $configPath "OpenClaw config"

if (-not (Test-Path -LiteralPath $LogDir)) {
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

if ($RegisterStartupRecovery) {
  $self = $MyInvocation.MyCommand.Path
  $argument = "-NoProfile -ExecutionPolicy Bypass -File `"$self`""
  $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
  $triggerAtLogon = New-ScheduledTaskTrigger -AtLogOn
  $triggerDaily = New-ScheduledTaskTrigger -Daily -At 7:05am
  Register-ScheduledTask -TaskName $RecoveryTaskName -Action $action -Trigger @($triggerAtLogon, $triggerDaily) -Force | Out-Null
  Write-Step "Registered startup recovery task: $RecoveryTaskName"
}

Write-Step "Starting local proxy task"
$proxyArg = "`"$proxyScript`""
Register-Task -TaskName $ProxyTaskName -Execute $NodeExe -Argument $proxyArg

if (-not (Wait-HttpOk "http://127.0.0.1:$ProxyPort/line/webhook" 15)) {
  throw "Local proxy did not become healthy at http://127.0.0.1:$ProxyPort/line/webhook"
}
Write-Step "Local proxy healthy"

Remove-Item -LiteralPath $tunnelOut, $tunnelErr -ErrorAction SilentlyContinue
Write-Step "Starting Cloudflare quick tunnel task"
$tunnelCommand = "/c $NpxCmd -y cloudflared tunnel --url http://127.0.0.1:$ProxyPort 1>$tunnelOut 2>$tunnelErr"
Register-Task -TaskName $TunnelTaskName -Execute "cmd.exe" -Argument $tunnelCommand

$deadline = (Get-Date).AddSeconds(45)
$tunnelUrl = $null
do {
  Start-Sleep -Seconds 2
  $tunnelUrl = Get-TunnelUrl $tunnelErr
  if (-not $tunnelUrl) {
    $tunnelUrl = Get-TunnelUrl $tunnelOut
  }
} while (-not $tunnelUrl -and (Get-Date) -lt $deadline)

if (-not $tunnelUrl) {
  throw "Could not find trycloudflare.com URL in $tunnelErr or $tunnelOut"
}

$webhookUrl = "$tunnelUrl/line/webhook"
Write-Step "Tunnel URL: $webhookUrl"

Write-Step "Updating LINE webhook endpoint and running official LINE test"
Invoke-NodeLineApi -ConfigPath $configPath -Endpoint $webhookUrl

Write-Step "Done"
