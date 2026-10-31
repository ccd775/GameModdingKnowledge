# Usage: pbzx_run.ps1 <outSub> <cmd> <args...>   (runs PbzExport against the installed game paks)
# Game folder (holds ProjectPBZ) and work root come from -GameDir / PBZ_GAME_DIR and -WorkRoot / PBZ_WORK_ROOT (or PBZ_ROOT).
# usmap: <work>\tools\Mappings.usmap if present (else "-"); AES: <work>\tools\aes.txt if present; Oodle: <work>\tools\oo2core_9_win64.dll.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Position = 0)][string]$OutSub,
      [string]$GameDir = $env:PBZ_GAME_DIR,
      [string]$WorkRoot = ($env:PBZ_WORK_ROOT ?? $env:PBZ_ROOT),
      [string]$Paks,
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
[Console]::OutputEncoding = [Text.Encoding]::UTF8
if (-not $WorkRoot -or (-not $GameDir -and -not $Paks)) { throw 'set -WorkRoot / PBZ_WORK_ROOT and -GameDir / PBZ_GAME_DIR (or -Paks)' }
$exe = Join-Path $WorkRoot 'tools\PbzExport\PbzExport.exe'
$usmap = Join-Path $WorkRoot 'tools\Mappings.usmap'; if (-not (Test-Path $usmap)) { $usmap = '-' }
$oodle = Join-Path $WorkRoot 'tools\oo2core_9_win64.dll'
$aesFile = Join-Path $WorkRoot 'tools\aes.txt'
if ((Test-Path $aesFile) -and -not $env:PBZX_AES) { $env:PBZX_AES = (Get-Content $aesFile -Raw).Trim() }
if (-not $Paks) { $Paks = Join-Path $GameDir 'ProjectPBZ\Content\Paks' }
& $exe $Paks $usmap $oodle (Join-Path $WorkRoot "extract\$OutSub") @Rest 2>&1
