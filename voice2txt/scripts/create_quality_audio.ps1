param([string]$Corpus = 'quality')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
Add-Type -AssemblyName System.Speech
# quality：一般語句；disfluent：含贅詞、重複與口誤更正，用來驗證 LLM 整理。
$voice2txtCorpus = Get-Content -LiteralPath "tests\fixtures\$Corpus-corpus.json" -Encoding UTF8 -Raw | ConvertFrom-Json
$voice2txtSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    foreach ($voice2txtCase in $voice2txtCorpus) {
        $voice2txtVoice = if ($voice2txtCase.language -eq 'zh') { 'Microsoft Hanhan Desktop' } else { 'Microsoft Zira Desktop' }
        $voice2txtSynth.SelectVoice($voice2txtVoice)
        $voice2txtSynth.SetOutputToWaveFile((Join-Path (Get-Location) "tests\fixtures\$Corpus-$($voice2txtCase.id).wav"))
        $voice2txtSynth.Speak($voice2txtCase.text)
        $voice2txtSynth.SetOutputToNull()
    }
} finally {
    $voice2txtSynth.Dispose()
}
