# Exports vanilla ascii meshes of one streaming group for the given LODs with ds2_pc_mi_022 (clean root, no mod layers).
# Usage: export_group.ps1 -Group 7e9d -Name porter -Lods 0,1,2 [-Tool <tool root>] [-WorkRoot <dir>]
# (-Tool / -WorkRoot: another build's root, e.g. one rebuilt from a player's collect.ps1 zip, and where its exports go;
#  defaults: DS2_ROOT\LocalCacheWinGame when DS2_ROOT is set, else DS2_MODDING\clean\LocalCacheWinGame, and DS2_MODDING\work)
param([string]$Group, [string]$Name, [string]$Lods = "0", [string]$Tool, [string]$WorkRoot)
$ErrorActionPreference = 'Stop'
if (-not $env:DS2_MODDING) { throw 'set DS2_MODDING (the modding workspace: clean\, work\, out\, backup\, tools\)' }
$M = $env:DS2_MODDING
if (-not $Tool) { $Tool = if ($env:DS2_ROOT) { Join-Path $env:DS2_ROOT 'LocalCacheWinGame' } else { Join-Path $M 'clean\LocalCacheWinGame' } }
if (-not $WorkRoot) { $WorkRoot = Join-Path $M 'work' }
$Out = Join-Path $WorkRoot $Name
Set-Location $Tool
foreach ($lod in $Lods.Split(",")) {
    Get-ChildItem -File | Where-Object { $_.Extension -in '.core', '.stream', '.ascii', '.matrices', '.txt', '.SkeletonHelpers', '.log' } | Remove-Item
    $dst = Join-Path $Out "lod$lod"
    New-Item -ItemType Directory -Force $dst | Out-Null
    & .\ds2_pc_mi_022.exe $Group $lod 2>&1 | Out-File -Encoding utf8 (Join-Path $dst 'export.log')
    Get-ChildItem -File | Where-Object { $_.Extension -in '.ascii', '.matrices', '.txt', '.SkeletonHelpers' } | Move-Item -Destination $dst -Force
    $core = Get-ChildItem -File -Filter '*.core' | Select-Object -First 1
    if ($core) { Move-Item $core.FullName (Join-Path $Out ($core.Name + '.pristine')) -Force }
    "lod $lod -> $dst : " + ((Get-ChildItem $dst -Filter *.ascii).Name -join ' ')
}
Get-ChildItem -File | Where-Object { $_.Extension -in '.core', '.stream' } | Remove-Item
