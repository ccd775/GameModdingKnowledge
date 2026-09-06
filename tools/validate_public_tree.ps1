[CmdletBinding()]
param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
& $Python -B (Join-Path $PSScriptRoot 'check_repository.py')
exit $LASTEXITCODE
