# Exports vanilla ascii meshes of one streaming group for the given LODs with ds2_pc_mi_022 (clean root, no mod layers).
# Usage: export_group.ps1 -Group 7e9d -Name porter -Lods 0,1,2
param([string]$Group, [string]$Name, [string]$Lods = "0")
$ErrorActionPreference = 'Stop'
if (-not $env:DS2_MODDING) { throw 'set DS2_MODDING (the modding workspace: clean\, work\, out\, backup\, tools\)' }
$M = $env:DS2_MODDING
$Tool = Join-Path $M 'clean\LocalCacheWinGame'
$Out = Join-Path $M "work\$Name"
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
