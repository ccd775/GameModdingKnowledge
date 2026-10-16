# Cook the UE 4.11 BendGame mod project (port of the build machine's cook.bat; close the editor first).
# Usage: cook.ps1 <logName>   -> log <DG_WORK_ROOT>\out\<logName>.log; prints its "Success - " / "Failure - " lines.
# UE 4.11: DG_UE_ROOT (or -UERoot). Project folder with BendGame.uproject: DG_PROJECT (or -Project), default
# <DG_WORK_ROOT>\U411\BendGame (DG_WORK_ROOT or -WorkRoot). -cookall -iterate: only changed assets are cooked again.
# Cooked files: <project>\Saved\Cooked\WindowsNoEditor\BendGame\Content (make_pak.py's first argument).
# Keep the work and project paths free of spaces: the log path goes in as one -abslog=<path> argument.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Mandatory, Position = 0)][string]$LogName, [string]$WorkRoot = $env:DG_WORK_ROOT,
      [string]$UERoot = $env:DG_UE_ROOT, [string]$Project = $env:DG_PROJECT)
if (-not $WorkRoot) { throw 'Set DG_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $UERoot) { throw 'Set DG_UE_ROOT (or pass -UERoot) to the UE 4.11 install folder' }
if (-not $Project) { $Project = Join-Path $WorkRoot 'U411\BendGame' }
$log = Join-Path $WorkRoot "out\$LogName.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
& (Join-Path $UERoot 'Engine\Binaries\Win64\UE4Editor-Cmd.exe') (Join-Path $Project 'BendGame.uproject') -run=cook -targetplatform=WindowsNoEditor -cookall -iterate -unattended -nop4 "-abslog=$log" *> $null
Select-String -LiteralPath $log -SimpleMatch -CaseSensitive -Pattern 'Success - ', 'Failure - ' | ForEach-Object { $_.Line }
