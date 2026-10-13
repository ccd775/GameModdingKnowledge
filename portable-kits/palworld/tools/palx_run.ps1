# Usage: palx_run.ps1 <outSub> <cmd> <args...>   (runs PalExport against the installed game paks)
# Paks: <PAL_GAME_DIR>\Pal\Content\Paks (PAL_GAME_DIR or -GameDir = the Palworld install folder).
# Output: <PAL_WORK_ROOT>\extract\<outSub> (PAL_WORK_ROOT or -WorkRoot). PalExport.exe: -Exe, default
# <WorkRoot>\tools\PalExport\PalExport.exe. usmap: PAL_USMAP (or -Usmap), default <WorkRoot>\tools\Mappings.usmap.
# Oodle DLL: PAL_OODLE (or -Oodle), default <WorkRoot>\tools\oo2core_9_win64.dll.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Position = 0)][string]$OutSub, [string]$GameDir = $env:PAL_GAME_DIR, [string]$WorkRoot = $env:PAL_WORK_ROOT,
      [string]$Exe, [string]$Usmap = $env:PAL_USMAP, [string]$Oodle = $env:PAL_OODLE,
      [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
if (-not $GameDir) { throw 'Set PAL_GAME_DIR (or pass -GameDir) to the Palworld install folder' }
if (-not $WorkRoot) { throw 'Set PAL_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $Exe) { $Exe = Join-Path $WorkRoot 'tools\PalExport\PalExport.exe' }
if (-not $Usmap) { $Usmap = Join-Path $WorkRoot 'tools\Mappings.usmap' }
if (-not $Oodle) { $Oodle = Join-Path $WorkRoot 'tools\oo2core_9_win64.dll' }
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$paks = Join-Path $GameDir 'Pal\Content\Paks'
& $exe $paks $Usmap $Oodle (Join-Path $WorkRoot "extract\$OutSub") @Rest 2>&1
