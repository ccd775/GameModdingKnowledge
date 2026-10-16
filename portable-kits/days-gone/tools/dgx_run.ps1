# Usage: dgx_run.ps1 <outSub> <cmd> <args...>   (runs DgExport against the installed Days Gone paks)
# Paks: <DG_GAME_DIR>\BendGame\Content\Paks (DG_GAME_DIR or -GameDir = the Days Gone install folder).
# Output: <DG_WORK_ROOT>\out\<outSub> (DG_WORK_ROOT or -WorkRoot). DgExport.exe: -Exe, default
# <DG_WORK_ROOT>\tools\DgExport\DgExport.exe. DGX_GAME (CUE4Parse engine version, default GAME_DaysGone; GAME_UE4_11 for
# stock UE 4.11 mod packages) and DGX_EXTRA (more folders to mount, ';'-separated) reach DgExport unchanged.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Mandatory, Position = 0)][string]$OutSub, [Parameter(Mandatory, Position = 1)][string]$Cmd,
      [string]$GameDir = $env:DG_GAME_DIR, [string]$WorkRoot = $env:DG_WORK_ROOT, [string]$Exe,
      [Parameter(ValueFromRemainingArguments)][string[]]$Rest)
if (-not $GameDir) { throw 'Set DG_GAME_DIR (or pass -GameDir) to the Days Gone install folder' }
if (-not $WorkRoot) { throw 'Set DG_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $Exe) { $Exe = Join-Path $WorkRoot 'tools\DgExport\DgExport.exe' }
$env:DOTNET_gcServer = '0'
& $Exe (Join-Path $GameDir 'BendGame\Content\Paks') (Join-Path $WorkRoot "out\$OutSub") $Cmd @Rest
