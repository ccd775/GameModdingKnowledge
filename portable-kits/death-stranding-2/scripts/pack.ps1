# Packs NN_OFFSET.core / NN_OFFSET_mesh.stream / _texture.stream files with id-daemon's Decima_pack_ds2 into
# package.18.00.core.stream (graph file index 0x80, LanguagePortugueseLA) and a patched streaming_graph.core.
# Usage: pack.ps1 -ModDir <dir with mod files> -Name <output name>
param([string]$ModDir, [string]$Name)
$ErrorActionPreference = 'Stop'
if (-not $env:DS2_MODDING) { throw 'set DS2_MODDING (the modding workspace: clean\, work\, out\, backup\, tools\)' }
$M = $env:DS2_MODDING
$Tool = Join-Path $M 'clean\LocalCacheWinGame'
$Pkg = Join-Path $Tool 'package'
$Out = Join-Path $M "out\$Name"
Set-Location $Tool
# Decima_pack patches streaming_graph.core in place: always start from the vanilla graph (independent copy, not a link)
Remove-Item (Join-Path $Pkg 'streaming_graph.core') -Force
Copy-Item (Join-Path $Pkg 'streaming_graph.core.org') (Join-Path $Pkg 'streaming_graph.core')
$PackDir = Join-Path $Tool 'pack'
if (Test-Path $PackDir) { Remove-Item $PackDir -Recurse -Force }
New-Item -ItemType Directory $PackDir | Out-Null
Get-ChildItem $ModDir -File | Where-Object { $_.Name -match '^[0-9A-F]{2}_[0-9A-F]{8}(\.core|_mesh\.stream|_texture\.stream)$' } | Copy-Item -Destination $PackDir
$n = (Get-ChildItem $PackDir).Count
Remove-Item 'package.18.00.core.stream' -ErrorAction SilentlyContinue
& .\Decima_pack_ds2.exe package.18.00.core.stream 80 2>&1 | Out-String | Set-Content (Join-Path $Tool 'pack.log')
New-Item -ItemType Directory -Force $Out | Out-Null
Move-Item 'package.18.00.core.stream' (Join-Path $Out 'package.18.00.core.stream') -Force
Copy-Item (Join-Path $Pkg 'streaming_graph.core') (Join-Path $Out 'streaming_graph.core') -Force
Copy-Item (Join-Path $Tool 'pack.log') $Out -Force
$log = Get-Content (Join-Path $Out 'pack.log')
"$n files packed; core redirects: " + ($log | Where-Object { $_ -match 'replacing core' }).Count + "; stream redirects: " + ($log | Where-Object { $_ -match 'replacing stream' }).Count
Get-ChildItem $Out | Select-Object Name, Length | Format-Table -AutoSize | Out-String
# restore the clean root graph
Remove-Item (Join-Path $Pkg 'streaming_graph.core') -Force
Copy-Item (Join-Path $Pkg 'streaming_graph.core.org') (Join-Path $Pkg 'streaming_graph.core')
Remove-Item $PackDir -Recurse -Force
