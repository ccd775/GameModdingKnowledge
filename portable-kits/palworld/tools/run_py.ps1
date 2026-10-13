# Usage: run_py.ps1 <script.py> "<script args>" <log>  -> runs an editor Python script in the Pal project (commandlet)
# and prints the [KARIN] / error lines of the log.
# UE 5.1 install: PAL_UE_ROOT (or -UERoot). Project folder with Pal.uproject: PAL_PROJECT (or -Project),
# default <PAL_WORK_ROOT>\UEProject\Pal (PAL_WORK_ROOT or -WorkRoot).
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Position = 0)][string]$Script, [Parameter(Position = 1)][string]$ScriptArgs, [Parameter(Position = 2)][string]$Log,
      [string]$UERoot = $env:PAL_UE_ROOT, [string]$Project = $env:PAL_PROJECT, [string]$WorkRoot = $env:PAL_WORK_ROOT)
if (-not $UERoot) { throw 'Set PAL_UE_ROOT (or pass -UERoot) to the UE 5.1 install folder' }
if (-not $Project) {
    if (-not $WorkRoot) { throw 'Set PAL_PROJECT (or pass -Project) to the folder with Pal.uproject, or PAL_WORK_ROOT (or -WorkRoot)' }
    $Project = Join-Path $WorkRoot 'UEProject\Pal'
}
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$UE = Join-Path $UERoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Proj = Join-Path $Project 'Pal.uproject'
New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null
$t0 = Get-Date
& $UE $Proj -run=pythonscript -script="$Script $ScriptArgs" -unattended -nosplash -nop4 -NoLogTimes -abslog="$Log" | Out-Null
"exit=$LASTEXITCODE minutes={0:N1}" -f ((Get-Date) - $t0).TotalMinutes
Select-String -Path $Log -Pattern '\[KARIN\]|Error|LogPython|PalGraphLib' | Select-Object -Last 80 | ForEach-Object { $_.Line }
