[CmdletBinding()]
param([switch]$Deep, [switch]$AsJson, [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if ($Deep) { Write-Warning 'Public checkout: original private evidence hashes cannot be revalidated here.' }
& $Python -B (Join-Path $root 'tools/check_repository.py') $root
exit $LASTEXITCODE
