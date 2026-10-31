# Installs or removes a packed mod in the game. Never writes into existing game files in place: the clean root holds
# hard links to them, so files are unlinked first and then replaced by new copies.
# Usage: install.ps1 -Name <out name>     |     install.ps1 -Restore
param([string]$Name, [switch]$Restore)
$ErrorActionPreference = 'Stop'
if (-not $env:DS2_MODDING) { throw 'set DS2_MODDING (the modding workspace: clean\, work\, out\, backup\, tools\)' }
$M = $env:DS2_MODDING
if (-not $env:DS2_GAME_DIR) { throw 'set DS2_GAME_DIR (the game folder with DS2.exe)' }
$GPkg = Join-Path $env:DS2_GAME_DIR 'LocalCacheWinGame\package'
$Backup = Join-Path $M 'backup'
$Files = 'streaming_graph.core', 'package.18.00.core.stream', 'streaming_links.stream'   # links only when the mod ships one
$VanillaGraph = '2ECAB7038B9B4AF650B0DB9E817389B63DD79B056DA02A13AA36945FF88DF380'

if (Get-Process DS2 -ErrorAction SilentlyContinue) { throw 'DS2.exe is running' }
New-Item -ItemType Directory -Force $Backup | Out-Null
foreach ($f in $Files) {
    $b = Join-Path $Backup $f
    if ($f -eq 'streaming_links.stream' -and (Get-Item (Join-Path $GPkg $f)).Length -ne 30226923) { throw 'game links file is not vanilla size' }
    if (-not (Test-Path $b)) {
        if ($f -eq 'streaming_graph.core' -and (Get-FileHash (Join-Path $GPkg $f)).Hash -ne $VanillaGraph) { throw 'game graph is not vanilla; refusing to back it up' }
        Copy-Item (Join-Path $GPkg $f) $b
        "backed up $f"
    }
}
$src = if ($Restore) { $Backup } else { Join-Path $M "out\$Name" }
if (-not $Restore) {   # a missing package or graph would silently fall back to the vanilla backup below
    foreach ($f in 'streaming_graph.core', 'package.18.00.core.stream') { if (-not (Test-Path (Join-Path $src $f))) { throw "$src has no $f" } }
}
foreach ($f in $Files) {
    $from = Join-Path $src $f
    if (-not (Test-Path $from)) { $from = Join-Path $Backup $f }   # mods without their own links file get vanilla back
    $dst = Join-Path $GPkg $f
    Remove-Item $dst -Force          # unlink (clean-root hard links keep the vanilla data)
    Copy-Item $from $dst
}
Get-ChildItem $GPkg | Where-Object { $_.Name -in $Files } | ForEach-Object { '{0} {1} {2}' -f $_.Name, $_.Length, (Get-FileHash $_.FullName -Algorithm MD5).Hash }
