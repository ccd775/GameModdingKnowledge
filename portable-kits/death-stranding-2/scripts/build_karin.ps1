# Full Karin build: build_ds2 -> dds -> mod (Porter groups, Sam's hair cover 50121, hair atlas 67704) -> pack, plus a link
# table. 50121: LodMesh 82 carries Karin's ears / bangs / side locks, every other mesh collapses (v3..v14 collapsed all of
# it in a separate pass, the build_v3 tail, which also set hide flags the game ignores).
# -Face: expression build, Karin's face in Sam's face skin (needs the v8f links: face LOD0/1 -> 186, part 43 vanilla).
# Usage: build_karin.ps1 -Name karin_v15 -Links streaming_links_v7.stream [-Face] [-Vrm <model.vrm>]   (links file in
# the work dir; DS2_MODDING is the modding workspace, -Vrm defaults to DS2_VRM)
param([string]$Name, [string]$Links, [switch]$Face, [string]$Vrm = $env:DS2_VRM)
$ErrorActionPreference = 'Stop'
if (-not $env:DS2_MODDING) { throw 'set DS2_MODDING (the modding workspace: clean\, work\, out\, backup\, tools\)' }
if (-not $Vrm) { throw 'set DS2_VRM (the source VRM) or pass -Vrm' }
$M = $env:DS2_MODDING
$R = Join-Path $M 'work'
$Py = $PSScriptRoot
$W = Join-Path $R 'karin\v1'
$Skel = Join-Path $R 'skeletons'
Set-Location $Py
$FaceArgs = if ($Face) { '--face', '--face-ref', "$R\g50120", '--face-tex', "$R\g67673", '--face-motion', "$R\porter\face_motion.json" } else { @() }
python build_ds2.py --vrm $Vrm --ref "$R\porter" --coat-ref "$R\g50110" --hair-ref "$R\g50121" --hair-tex "$R\g67704" --hair-used "$R\g50121\hair_used.png" --boot-ref "$R\g31123" --skeletons $Skel --work $W @FaceArgs 2>&1 | Tee-Object -FilePath (Join-Path $W 'build_ds2.log') | Select-Object -Last 8
if ($LASTEXITCODE) { throw 'build_ds2 failed' }
python make_dds.py $W (Join-Path $M 'tools\texconv.exe') | Select-Object -Last 2
if ($LASTEXITCODE) { throw 'make_dds failed' }
$C = Join-Path $W 'collapse50121'
if (Test-Path $C) { Remove-Item $C -Recurse -Force }
python gen_collapse.py $C $Skel "$R\g50121:1a0d:50121" --skel=1A0C:1A0C_skel_0.ascii | Select-Object -Last 1
if ($LASTEXITCODE) { throw 'gen_collapse 50121 failed' }
# stream-only collapses (every mesh of the group collapses in place, counts kept):
# 12706 - the player stand-in that scripted scenes (many cutscenes) spawn with DSPlayerTakeOverState; its model is
#   Sam's whole head of hair (16 parts, skeleton 12715)
# 6744 - the private-room shower scene: it copies Karin's covers onto its own actors and shows a hair-only actor
#   (model 6744:433, skeleton 67712) carrying Sam's wet hair, 7 LodMeshes / 23 meshes, all the group has
$Extra = @()
foreach ($e in @(@(12706, '2deb'), @(6744, '7e9e'))) {
    $C2 = Join-Path $W "collapse$($e[0])"
    if (Test-Path $C2) { Remove-Item $C2 -Recurse -Force }
    python gen_collapse.py $C2 $Skel "$R\g$($e[0]):$($e[1]):$($e[0])" --stream-only | Select-Object -Last 1
    if ($LASTEXITCODE) { throw "gen_collapse $($e[0]) failed" }
    $Extra += Join-Path $C2 'jobs.json'
}
& (Join-Path $PSScriptRoot 'make_mod_ds2.ps1') -Work $W -Name $Name -Collapse (@((Join-Path $W 'collapse\jobs.json'), (Join-Path $C 'jobs.json')) + $Extra) -Face:$Face
Copy-Item (Join-Path $W $Links) (Join-Path $M "out\$Name\streaming_links.stream") -Force
Get-ChildItem (Join-Path $M "out\$Name") | ForEach-Object { '{0} {1}' -f $_.Name, $_.Length }
