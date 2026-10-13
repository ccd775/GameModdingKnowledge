# Build-machine cook + legacy pak (V11) for the Pal authoring project.
# Usage: pwsh -File cook_and_pack.ps1 [-SkipCook] [-Install] [-Tag r1]
# Paks (all mounted at ../../../, i.e. paths start with Pal/Content/...):
#   Karin_Body_P     body mesh (default outfit OldCloth001), cloth-layer physics ABP, Mods/KarinPal (MIs, textures)
#   Karin_Face_P     every female head mesh -> Karin face with the PalFacialComponent morphs
#   Karin_HideHair_P every hair mesh -> one invisible triangle
# Dummies (skeleton, physics asset, parent materials, ALI_HumanCloth) are cooked but never staged.
# Working folder: PAL_WORK_ROOT (or -WorkRoot; logs\, stage\<tag>\, out\<tag>\). UE 5.1 install: PAL_UE_ROOT (or -UERoot).
# Project folder with Pal.uproject: PAL_PROJECT (or -Project), default <WorkRoot>\UEProject\Pal.
# repak.exe: -Repak, default <WorkRoot>\tools\repak.exe. -Install copies the paks to <PAL_GAME_DIR>\Pal\Content\Paks\~mods
# (PAL_GAME_DIR or -GameDir = the Palworld install folder).
[CmdletBinding(PositionalBinding = $false)]
param(
    [switch]$SkipCook,
    [switch]$Install,
    [Parameter(Position = 0)][string]$Tag = 'dev',
    [string]$WorkRoot = $env:PAL_WORK_ROOT, [string]$UERoot = $env:PAL_UE_ROOT, [string]$Project = $env:PAL_PROJECT,
    [string]$GameDir = $env:PAL_GAME_DIR, [string]$Repak
)
$ErrorActionPreference = 'Stop'
if (-not $WorkRoot) { throw 'Set PAL_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $UERoot) { throw 'Set PAL_UE_ROOT (or pass -UERoot) to the UE 5.1 install folder' }
if ($Install -and -not $GameDir) { throw 'Set PAL_GAME_DIR (or pass -GameDir) to the Palworld install folder for -Install' }
if (-not $Project) { $Project = Join-Path $WorkRoot 'UEProject\Pal' }
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Root = (Resolve-Path -LiteralPath $WorkRoot).ProviderPath.TrimEnd('\')
$ProjDir = (Resolve-Path -LiteralPath $Project).ProviderPath.TrimEnd('\')
$UE = Join-Path $UERoot 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Proj = "$ProjDir\Pal.uproject"
$Cooked = "$ProjDir\Saved\Cooked\Windows\Pal\Content"
if (-not $Repak) { $Repak = "$Root\tools\repak.exe" }
$Mods = if ($GameDir) { Join-Path $GameDir 'Pal\Content\Paks\~mods' } else { $null }

$Paks = [ordered]@{
    'Karin_Body_P'     = @('Pal\Model\Character\Player\Outfit\SK_Player_Female_Outfit_OldCloth001\SK_Player_Female_Outfit_OldCloth001.*',
                           'Pal\Blueprint\Character\Player\Imp_Cloth\ABP_F_OldCloth001_Implimentation.*',
                           'Mods\KarinPal\*')
    'Karin_Face_P'     = @('Pal\Model\Character\Player\Head\*\SK_Player_Female_Head*.*')
    'Karin_HideHair_P' = @('Pal\Model\Character\Player\Hair\*\SK_Player_Hair*.*')
}

if (-not $SkipCook) {
    $log = "$Root\logs\cook_$Tag.log"
    New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
    $t0 = Get-Date
    & $UE $Proj -run=cook -targetplatform=Windows -unversioned -iterate -unattended -nop4 -NoLogTimes -nosplash -abslog="$log" | Out-Null
    "cook exit=$LASTEXITCODE minutes={0:N1}" -f ((Get-Date) - $t0).TotalMinutes
    Get-Content $log -Tail 8
    if (-not (Select-String -Path $log -Pattern 'Success - 0 error' -Quiet)) { throw "cook did not report success, see $log" }
}

function Stage-Files([string[]]$Globs, [string]$Stage) {
    Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue
    foreach ($g in $Globs) {
        $rel = Split-Path $g
        $leaf = Split-Path $g -Leaf
        $parts = $rel -split '\\'
        # expand wildcard directories (e.g. Head\*) relative to the cooked content root
        $dirs = @(Get-Item -Path (Join-Path $Cooked $rel) -ErrorAction SilentlyContinue)
        foreach ($d in $dirs) {
            $recurse = $leaf -eq '*'
            $files = if ($recurse) { Get-ChildItem -Path $d.FullName -Recurse -File } else { Get-ChildItem -Path $d.FullName -Filter $leaf -File }
            foreach ($f in $files) {
                $r = $f.FullName.Substring($Cooked.Length + 1)
                $dst = Join-Path "$Stage\Pal\Content" $r
                New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
                Copy-Item $f.FullName $dst
            }
        }
    }
}

New-Item -ItemType Directory -Force "$Root\out\$Tag" | Out-Null
foreach ($name in $Paks.Keys) {
    $stage = "$Root\stage\$Tag\$name"
    Stage-Files $Paks[$name] $stage
    $files = Get-ChildItem -Recurse -File $stage
    "== $name staged $($files.Count) files"
    $files | ForEach-Object { '  {0,10} {1}' -f $_.Length, $_.FullName.Substring($stage.Length) } | Select-Object -First 30
    $pak = "$Root\out\$Tag\$name.pak"
    Remove-Item -Force $pak -ErrorAction SilentlyContinue
    & $Repak pack --version V11 --mount-point '../../../' $stage $pak
    if ($LASTEXITCODE -ne 0) { throw "repak failed for $name" }
    $h = Get-FileHash -Algorithm SHA256 $pak
    '  pak {0} bytes sha256 {1}' -f (Get-Item $pak).Length, $h.Hash.Substring(0, 16)
}

if ($Install) {
    New-Item -ItemType Directory -Force $Mods | Out-Null
    Copy-Item "$Root\out\$Tag\*.pak" $Mods -Force
    "installed to $Mods"; Get-ChildItem $Mods | ForEach-Object { '  {0,10} {1}' -f $_.Length, $_.Name }
}
