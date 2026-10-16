# Install the staged mod pak after checking its SHA-256 (port of the build machine's swap.ps1).
# Usage: install_pak.ps1 <sha256> [-Name zz_Karin_P]
# Staged pak: <DG_WORK_ROOT>\staging\<Name>.pak (DG_WORK_ROOT or -WorkRoot). Target folder:
# <DG_GAME_DIR>\BendGame\Content\Paks\~mods (DG_GAME_DIR or -GameDir). A non-empty pak already installed under that name
# is moved to <DG_WORK_ROOT>\disabled_mods\<Name>_prev.pak first (overwriting the previous one there).
# Refuses (exit 1, nothing moved) while DaysGone or UE4Editor runs, when no pak is staged, or when the hash differs.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Mandatory, Position = 0)][string]$Sha, [string]$Name = 'zz_Karin_P',
      [string]$WorkRoot = $env:DG_WORK_ROOT, [string]$GameDir = $env:DG_GAME_DIR)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
if (-not $WorkRoot) { throw 'Set DG_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $GameDir) { throw 'Set DG_GAME_DIR (or pass -GameDir) to the Days Gone install folder' }
$M = Join-Path $GameDir 'BendGame\Content\Paks\~mods'
$s = Join-Path $WorkRoot "staging\$Name.pak"
$dst = Join-Path $M "$Name.pak"
$prev = Join-Path $WorkRoot "disabled_mods\${Name}_prev.pak"
if (Get-Process DaysGone, UE4Editor -ErrorAction SilentlyContinue) { 'busy: game or editor running'; exit 1 }
if (-not (Test-Path -LiteralPath $s)) { "no staged pak: $s"; exit 1 }
if ((Get-FileHash -LiteralPath $s).Hash.ToLower() -ne $Sha.ToLower()) { 'staged pak hash mismatch'; exit 1 }
New-Item -ItemType Directory -Force $M, (Split-Path $prev) | Out-Null
if ((Test-Path -LiteralPath $dst) -and (Get-Item -LiteralPath $dst).Length -gt 0) {
  Move-Item -LiteralPath $dst -Destination $prev -Force }
Move-Item -LiteralPath $s -Destination $dst -Force
'installed ' + (Get-FileHash -LiteralPath $dst).Hash.Substring(0, 12)
