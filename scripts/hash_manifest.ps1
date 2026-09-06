[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Path,
  [Parameter(Mandatory=$true)][string]$Output,
  [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$tool = Join-Path $PSScriptRoot '../portable-kits/common/modkit.py'
& $Python -B $tool inventory $Path --output $Output
exit $LASTEXITCODE
