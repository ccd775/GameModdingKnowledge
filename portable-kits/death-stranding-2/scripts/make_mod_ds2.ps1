# Imports Karin meshes, collapses and textures into the Porter groups with ds2_pc_mi_022, patches the cores and packs.
# Usage: make_mod_ds2.ps1 -Work <DS2_MODDING>\work\karin\v1 -Name karin_v1 [-Collapse <jobs.json>, ...]
param([string]$Work, [string]$Name, [string[]]$Collapse = @(), [switch]$Face)
$ErrorActionPreference = 'Stop'
if (-not $env:DS2_MODDING) { throw 'set DS2_MODDING (the modding workspace: clean\, work\, out\, backup\, tools\)' }
$M = $env:DS2_MODDING
$Tool = Join-Path $M 'clean\LocalCacheWinGame'
$Py = $PSScriptRoot
$Skel = Join-Path $M 'work\skeletons'
# vanilla cores of build 1.0.48.0 (export_group.ps1 keeps each export's core as <name>.core.pristine)
$Pristine = @{
    50108 = Join-Path $M 'work\porter\14_3BB15CCB.core.pristine'
    50109 = Join-Path $M 'work\g50109\14_12F20FB7.core.pristine'
    50110 = Join-Path $M 'work\g50110\14_12EC40C1.core.pristine'
    50113 = Join-Path $M 'work\g50113\14_12F9A95F.core.pristine'
    50116 = Join-Path $M 'work\g50116\14_3633EDA9.core.pristine'
    50121 = Join-Path $M 'work\g50121\13_413938B0.core.pristine'
    50120 = Join-Path $M 'work\g50120\13_41435720.core.pristine'
    67699 = Join-Path $M 'work\g67699\13_542A44E9.core.pristine'   # raw span bytes (no meshes, not tool-exported)
}
# core-only patches from build_ds2 (<work>\fields.json: {gid: [field patches]}): Sam's hair PBD body 67699:2, which
# Karin's ears, bangs and side locks follow (fluctuation off, the ear strands' MaxDistance scaled)
$FieldPatches = @{}
$fj = Join-Path $Work 'fields.json'
if (Test-Path $fj) { (Get-Content $fj -Raw | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $FieldPatches[[int]$_.Name] = @($_.Value) } }
# Porter facial model parts (ArtPartsModelResource 50108:59): Karin's head is in the body mesh; 11 = hair (since v2)
$HideParts = 302, 51, 27, 45, 43, 46, 36, 40, 29, 38, 30, 42, 48, 11
# face build: Karin's face is the face skin part 43 (under root part 302) -> those stay visible
if ($Face) { $HideParts = @($HideParts | Where-Object { $_ -notin 302, 43 }) }
# timefall corrosion: the game drives CorrosionRate (shader variable id 852864580) on the suit materials. A long, wet
# save greyed Karin's body, gloves, coat and Porter boots with a fibrous wear layer (her hair and face materials lack
# the variable and stayed clean; a private-room shower reset it). Renamed in those groups' render effects, the game
# drives nothing there and they keep 0.
$RenameVars = @{ 50108 = @{ '852864580' = 852864581 }; 50110 = @{ '852864580' = 852864581 } }

Set-Location $Tool
Get-ChildItem -File | Where-Object { $_.Extension -in '.core', '.stream', '.ascii', '.matrices', '.txt', '.SkeletonHelpers', '.log' } | Remove-Item
$log = Join-Path $Work 'make.log'
Remove-Item $log -ErrorAction SilentlyContinue
# collapse jobs cover whole groups; meshes that build_ds2 fills (Porter slots, the coat) are skipped there
$jobs = @(Get-Content (Join-Path $Work 'jobs.json') -Raw | ConvertFrom-Json)
$own = @{}
foreach ($j in $jobs) { $own["$($j.gid):$($j.mesh)"] = 1 }
if (-not $Collapse) { $Collapse = @(Join-Path $Work 'collapse\jobs.json') }
foreach ($c in $Collapse) {
    $jobs += @(Get-Content $c -Raw | ConvertFrom-Json | Where-Object { -not $own.ContainsKey("$($_.gid):$($_.mesh)") })
}
foreach ($j in $jobs) {
    $out = & .\ds2_pc_mi_022.exe $j.group $j.lod (Join-Path $Skel $j.skel) $j.ascii $j.mesh 0 2>&1 | Out-String
    "### mesh $($j.group) lod $($j.lod) $($j.mesh)`n$out" | Add-Content $log
    $ok = ([regex]::Matches($out, '(?m)^success!\s*$')).Count
    $want = @($j.prims.PSObject.Properties).Count
    if ($ok -ne $want) { throw "mesh $($j.group)/$($j.mesh) lod $($j.lod): $ok of $want submeshes imported" }
}
"meshes: $($jobs.Count) imported"
foreach ($t in (Get-Content (Join-Path $Work 'textures.json') -Raw | ConvertFrom-Json)) {
    $out = & .\ds2_pc_mi_022.exe $t[0] 0 $t[2] $t[1] 2>&1 | Out-String
    "### texture $($t[0]) $($t[1])`n$out" | Add-Content $log
    $n = ([regex]::Matches($out, 'Replacing mip')).Count
    if ($n -lt 1) { throw "texture $($t[0])_$($t[1]) replaced no mip" }
}
"textures imported"
# stream-only groups (equipped boots in the player group 31123, the scene stand-ins' hair 12706 / 6744): the meshes
# keep their vertex / index counts, so the tool's core must equal the vanilla one; it stays out of the mod (31123's is
# 130 MB) and only the mesh streams are packed
$StreamOnly = @{
    31123 = Join-Path $M 'work\g31123\13_060BAEE1.core.pristine'
    12706 = Join-Path $M 'work\g12706\13_53F4132A.core.pristine'
    6744 = Join-Path $M 'work\g6744\1A_117FD3F5.core.pristine'
}
foreach ($gid in ($jobs | Where-Object { $_.stream_only } | ForEach-Object { $_.gid } | Sort-Object -Unique)) {
    $core = Join-Path $Tool ([IO.Path]::GetFileNameWithoutExtension($StreamOnly[[int]$gid]))
    if (-not (Test-Path $core)) { throw "stream-only group $gid`: the tool wrote no core $core" }
    $same = (Get-FileHash $core -Algorithm MD5).Hash -eq (Get-FileHash $StreamOnly[[int]$gid] -Algorithm MD5).Hash
    if (-not $same) {
        $d = python -c "import sys; a=open(sys.argv[1],'rb').read(); b=open(sys.argv[2],'rb').read(); d=[i for i in range(min(len(a),len(b))) if a[i]!=b[i]]; print(len(a), len(b), len(d), d[:20])" $core $StreamOnly[[int]$gid]
        throw "stream-only group $gid`: core changed (sizes, differing bytes, first offsets): $d"
    }
    Remove-Item $core
    "stream-only $gid`: core unchanged, left out"
}
foreach ($gid in ($jobs | Where-Object { -not $_.stream_only } | ForEach-Object { $_.gid } | Sort-Object -Unique)) {
    $core = Join-Path $Tool ([IO.Path]::GetFileNameWithoutExtension($Pristine[[int]$gid]))
    $meshes = @($jobs | Where-Object { $_.gid -eq $gid } | ForEach-Object {
        $h = @{ index = $_.mesh; prims = $_.prims }
        if ($_.ibm) { $h.ibm = $_.ibm }
        if ($_.ibm_post) { $h.ibm_post = $_.ibm_post }
        if ($_.no_cast_shadow) { $h.no_cast_shadow = $true }
        $h })
    $pj = @{ gid = [int]$gid; core = $core; pristine = $Pristine[[int]$gid]; streams = $Tool; out = $core; meshes = $meshes }
    if ($gid -eq 50108) { $pj.hide_parts = $HideParts }
    if ($RenameVars.ContainsKey([int]$gid)) { $pj.rename_vars = $RenameVars[[int]$gid] }
    $pjPath = Join-Path $Work "patch_$gid.json"
    $pj | ConvertTo-Json -Depth 8 | Set-Content $pjPath -Encoding ascii
    $r = python (Join-Path $Py 'patch_core.py') $pjPath 2>&1 | Out-String
    "### patch $gid`n$r" | Add-Content $log
    if ($LASTEXITCODE) { throw "patch_core failed for $gid`n$r" }
    "patched $gid"
}
foreach ($gid in $FieldPatches.Keys) {
    $core = Join-Path $Tool ([IO.Path]::GetFileNameWithoutExtension($Pristine[[int]$gid]))
    Copy-Item $Pristine[[int]$gid] $core -Force
    $pj = @{ gid = [int]$gid; core = $core; pristine = $Pristine[[int]$gid]; streams = $Tool; out = $core
             meshes = @(); fields = $FieldPatches[$gid] }
    $pjPath = Join-Path $Work "patch_$gid.json"
    $pj | ConvertTo-Json -Depth 8 | Set-Content $pjPath -Encoding ascii
    $r = python (Join-Path $Py 'patch_core.py') $pjPath 2>&1 | Out-String
    "### patch $gid`n$r" | Add-Content $log
    if ($LASTEXITCODE) { throw "patch_core failed for $gid`n$r" }
    "patched $gid (fields)"
}
$Mod = Join-Path $Work 'mod'
if (Test-Path $Mod) { Remove-Item $Mod -Recurse -Force }
New-Item -ItemType Directory $Mod | Out-Null
Get-ChildItem $Tool -File | Where-Object { $_.Extension -in '.core', '.stream' } | Copy-Item -Destination $Mod
"mod files: " + (Get-ChildItem $Mod).Count
& (Join-Path $PSScriptRoot 'pack.ps1') -ModDir $Mod -Name $Name
