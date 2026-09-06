[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ProjectRoot,
  [Parameter(Mandatory=$true)][string]$Game,
  [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$tool = Join-Path $PSScriptRoot '../portable-kits/common/modkit.py'
& $Python -B $tool init $ProjectRoot --game $Game
exit $LASTEXITCODE
