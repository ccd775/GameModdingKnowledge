# Builds a clean root for id-daemon's DS2 tools: package files are hard links to the game (never written),
# streaming_graph.core is an independent copy (Decima_pack writes it), sub-folders are junctions.
$ErrorActionPreference = 'Stop'
if (-not $env:DS2_GAME_DIR -or -not $env:DS2_MODDING) { throw 'set DS2_GAME_DIR (the game folder with DS2.exe) and DS2_MODDING (the modding workspace)' }
$Game = $env:DS2_GAME_DIR
$Clean = Join-Path $env:DS2_MODDING 'clean'
$GPkg = Join-Path $Game 'LocalCacheWinGame\package'
$CLc = Join-Path $Clean 'LocalCacheWinGame'
$CPkg = Join-Path $CLc 'package'

if (Test-Path (Join-Path $GPkg 'streaming_graph.core.org')) { throw 'game already has streaming_graph.core.org (modded?)' }
New-Item -ItemType Directory -Force $CPkg | Out-Null

New-Item -ItemType HardLink -Path (Join-Path $Clean 'DS2.exe') -Target (Join-Path $Game 'DS2.exe') -Force | Out-Null
foreach ($f in Get-ChildItem $GPkg -File) {
    if ($f.Name -eq 'streaming_graph.core') { continue }
    New-Item -ItemType HardLink -Path (Join-Path $CPkg $f.Name) -Target $f.FullName -Force | Out-Null
}
foreach ($d in Get-ChildItem $GPkg -Directory) {
    $link = Join-Path $CPkg $d.Name
    if (-not (Test-Path $link)) { New-Item -ItemType Junction -Path $link -Target $d.FullName | Out-Null }
}
New-Item -ItemType HardLink -Path (Join-Path $CPkg 'streaming_graph.core.org') -Target (Join-Path $GPkg 'streaming_graph.core') -Force | Out-Null
Copy-Item (Join-Path $GPkg 'streaming_graph.core') (Join-Path $CPkg 'streaming_graph.core') -Force

$Tool = Join-Path $env:DS2_MODDING 'tools\ds2_modtool'   # ds2_pc_mi_022.exe and Decima_pack_ds2.exe
Copy-Item (Join-Path $Tool 'ds2_pc_mi_022.exe') $CLc -Force
Copy-Item (Join-Path $Tool 'Decima_pack_ds2.exe') $CLc -Force
Set-Content -Path (Join-Path $CLc 'decima.ini') -Value ($CLc + '\') -Encoding ascii

Get-ChildItem $CPkg | Select-Object Name, Length, LinkType | Format-Table -AutoSize | Out-String -Width 200
(Get-FileHash (Join-Path $GPkg 'streaming_graph.core')).Hash
