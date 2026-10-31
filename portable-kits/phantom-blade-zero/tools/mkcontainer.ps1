# mkcontainer.ps1: IoStore container (+ companion pak) holding only the mod's real packages from the last cook.
# Dummies (skeletons, physics assets, ABP, parent materials) are cooked too but never listed here.
# Usage: pwsh -File mkcontainer.ps1 [-Mod original|pt] [-Root <work root>] [-UE <UE 5.7 root>] [-Out <dir>] [-Name <container>]
#        [-Exclude 'NameA+NameB'] (bisect variants)
# -Root (or PBZ_ROOT) holds UE\ProjectPBZ (cooked); -UE (or UE_ROOT) is the engine folder that holds Engine\. Defaults by
# -Mod: original -> z_KarinPBZ_P + Mods/KarinPBZ/KarinPBZ.txt, pt -> z_KarinPT_P + Mods/KarinPT/KarinPT.txt; -Out <Root>\out.
param([ValidateSet('original', 'pt')][string]$Mod = 'original', [string]$Root = $env:PBZ_ROOT, [string]$UE = $env:UE_ROOT,
      [string]$Out, [string]$Name, [string]$Exclude = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
if (-not $Root -or -not $UE) { throw 'set -Root / PBZ_ROOT (work root with UE\ProjectPBZ) and -UE / UE_ROOT (UE 5.7 install)' }
$tag = @{ original = 'KarinPBZ'; pt = 'KarinPT' }[$Mod]
$model = @{ original = 'Karin_Original'; pt = 'Karin_PicodraTech' }[$Mod]
if (-not $Name) { $Name = "z_${tag}_P" }
if (-not $Out) { $Out = Join-Path $Root 'out' }
$pak = Join-Path $UE 'Engine\Binaries\Win64\UnrealPak.exe'
$proj = Join-Path $Root 'UE\ProjectPBZ\ProjectPBZ.uproject'
$cooked = Join-Path $Root 'UE\ProjectPBZ\Saved\Cooked\Windows'
$meta = Join-Path $cooked 'ProjectPBZ\Metadata'
$plug = Join-Path $cooked 'ProjectPBZ\Plugins\HuaShira\Content'
$mount = '../../../ProjectPBZ/Plugins/HuaShira/Content/'
$real = @(
    'Characters\Hero\Hero_Hun\Hun_Invs',
    'Characters\Hero\Hero_Hun\Hun_CopyPose',
    'Characters\Hero\Hero_Hun\Hun_CopyPose_Head',
    'Characters\Hero\Hero_Hun\SkinParts\Hun_Body_Simple',
    'Characters\Hero\Hero_Hun_Climax\SkinParts\Hun_Body_Climax',
    'Characters\Hero\Hero_Hun\SkinParts\Hun_Head_New',
    'Characters\Hero\Hero_Hun\SkinParts\Hun_Cloth',
    'Characters\Hero\Hero_Hun\SkinParts\Hun_Scarf',
    'Characters\Hero\Hero_Hun\SkinParts\Hun_Scarf_Climax',
    'Characters\Hero\Hero_Hun\SkinParts\Hun_Hair_Band',
    'Characters\Hero\Hero_Hun\SkinParts\Hun_BrowLashCard',
    'Characters\Hero\Hero_Hun\SkinParts\Cloth\CA_Hun_UpperCloth',
    'Characters\Hero\Hero_Hun\SkinParts\Cloth\CA_Hun_Skirt',
    'Characters\Hero\Hero_Hun\SkinParts\Cloth\CA_Hun_Cape',
    'Characters\Hero\Hero_Hun\SkinParts\Cloth\CA_Hun_Hair01',
    'Characters\Hero\Hero_Hun\SkinParts\Cloth\CA_Hun_UpperCloth_Climax',
    'Characters\Hero\Hero_Hun\SkinParts\Cloth\CA_Hun_Skirt_Climax',
    'Characters\Hero\Hero_Hun\SkinParts\Cloth\CA_Hun_Cape_Climax',
    'Characters\Hero\Hero_Hun\Hats\Hun_Hat_00',
    'Characters\Hero\Hero_Hun\Hats\Hun_Hat_01',
    'Characters\Hero\Young_Hun\SkinParts\Hun_Young_Body',
    'Characters\Hero\Young_Hun\SkinParts\Hun_Young_Head',
    'Characters\Hero\Young_Hun\SkinParts\Hun_young_Hair',
    'Characters\Hero\Young_Hun\SkinParts\Hun_Young_BrowLashCard',
    'Characters\Hero\Young_Hun\SkinParts\Cloth\CA_Hun_YOung_Cloth02',
    'Characters\Hero\Young_Hun\SkinParts\Cloth\CA_Hun_Young_Hair01',
    'Characters\Hero\Young_Hun\SkinParts\Cloth\CA_Hun_Young_Cloth01'
)
$files = @()
$skip = if ($Exclude) { $Exclude.Split([char]43) } else { @() }
foreach ($r in $real) {
    if ($skip -contains (Split-Path $r -Leaf)) { continue }
    $hits = Get-ChildItem -Path (Join-Path $plug ($r + '.*')) -File
    if (-not ($hits | Where-Object Extension -eq '.uasset')) { throw "not cooked: $r" }
    $files += $hits
}
$files += Get-ChildItem -Path (Join-Path $plug 'Mods\KarinPBZ') -Recurse -File
# hidden stand-ins under the cutscene groom asset names, below the game content root
$game = Join-Path $cooked 'ProjectPBZ\Content'
$gameFiles = @('PBZContent\Characters\Hero\Hun_Young\Mesh\V02\Hair', 'PBZContent\Characters\Hero\Hun_New_V1\Mesh') |
    ForEach-Object { Get-ChildItem -Path (Join-Path $game $_) -File -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force $Out, (Join-Path $Out 'tmp') | Out-Null
$resp = Join-Path $Out 'resp.txt'
@($files | ForEach-Object {
    $rel = $_.FullName.Substring($plug.Length + 1).Replace('\', '/')
    '"{0}" "{1}{2}" -compress' -f $_.FullName, $mount, $rel
}) + @($gameFiles | ForEach-Object {
    $rel = $_.FullName.Substring($game.Length + 1).Replace('\', '/')
    '"{0}" "../../../ProjectPBZ/Content/{1}" -compress' -f $_.FullName, $rel
}) | Set-Content $resp -Encoding UTF8
$cmds = Join-Path $Out 'cmds.txt'
'-Output="{0}" -ContainerName={1} -ResponseFile="{2}"' -f (Join-Path $Out "$Name.utoc"), $Name, $resp | Set-Content $cmds -Encoding UTF8
& $pak $proj "-CreateGlobalContainer=$(Join-Path $Out 'tmp\global.utoc')" "-PackageStoreManifest=$(Join-Path $meta 'packagestore.manifest')" `
    "-CookedDirectory=$cooked" "-Commands=$cmds" "-ScriptObjects=$(Join-Path $meta 'scriptobjects.bin')" `
    -compressionformats=Oodle -compresslevel=4 -compressmethod=Kraken -platform=Windows -unattended 2>&1 | Select-String 'Error|Warning|Container|pakchunk|z_|Wrote|Display: .*(packages|chunks)' | Select-Object -Last 25
# companion pak (mounting the pak is what makes the engine pick up the .utoc next to it)
$note = Join-Path $Out "tmp\$tag.txt"
"$model replaces Hun (Phantom Blade Zero). Built by the PBZ mod project." | Set-Content $note -Encoding UTF8
$presp = Join-Path $Out 'pakresp.txt'
'"{0}" "../../../ProjectPBZ/Content/Mods/{1}/{1}.txt"' -f $note, $tag | Set-Content $presp -Encoding UTF8
& $pak (Join-Path $Out "$Name.pak") "-create=$presp" -platform=Windows -unattended 2>&1 | Select-String 'Error|Created|Added' | Select-Object -Last 5
Remove-Item -Recurse -Force (Join-Path $Out 'tmp')
"files listed: $($files.Count) + game $(@($gameFiles).Count)"
Get-ChildItem $Out -File | ForEach-Object { '{0,12} {1}' -f $_.Length, $_.Name }
