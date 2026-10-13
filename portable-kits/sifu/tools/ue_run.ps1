# Usage: ue_run.ps1 <script.py> [args...]  -> runs a python script in the Sifu project commandlet.
# Script arguments are passed through <SIFU_WORK_ROOT>\work\py_args.json (list of strings; its path reaches the script
# in the environment variable SIFU_PY_ARGS); log to <SIFU_WORK_ROOT>\logs.
# UE 4.26 install: SIFU_UE_ROOT (or -UERoot). Project folder with Sifu.uproject: SIFU_PROJECT (or -Project),
# default <SIFU_WORK_ROOT>\SifuProj.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Mandatory, Position = 0)][string]$Script, [string]$WorkRoot = $env:SIFU_WORK_ROOT,
      [string]$UERoot = $env:SIFU_UE_ROOT, [string]$Project = $env:SIFU_PROJECT,
      [Parameter(ValueFromRemainingArguments)][string[]]$Rest)
if (-not $WorkRoot) { throw 'Set SIFU_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $UERoot) { throw 'Set SIFU_UE_ROOT (or pass -UERoot) to the UE 4.26 install folder' }
if (-not $Project) { $Project = Join-Path $WorkRoot 'SifuProj' }
$logs = Join-Path $WorkRoot 'logs'
$log = Join-Path $logs ([IO.Path]::GetFileNameWithoutExtension($Script) + ".log")
New-Item -ItemType Directory -Force $logs | Out-Null
$env:SIFU_PY_ARGS = Join-Path $WorkRoot 'work\py_args.json'
ConvertTo-Json -InputObject @($Rest) | Set-Content -Encoding UTF8 $env:SIFU_PY_ARGS
& (Join-Path $UERoot 'Engine\Binaries\Win64\UE4Editor-Cmd.exe') (Join-Path $Project 'Sifu.uproject') -run=pythonscript "-script=$Script" -unattended -nullrhi -nosplash -nop4 > $log 2>&1
"exit=$LASTEXITCODE"
Select-String -Path $log -Pattern 'LogPython: Error|Traceback|Error:|_DONE|LogPython: Warning' | Select-Object -Last 30 | ForEach-Object { $_.Line }
