# One-time preparation for pipeline.ps1: bundle listing, vanilla extracts and WolvenKit JSONs under the work root.
#   pwsh prepare.ps1 [-GameDir <game>] [-WorkRoot <dir>] [-WolvenKitDir <extracted WolvenKit 7 nightly>]
# Defaults: $env:W3_GAME_DIR, $env:W3_WORK, $env:W3_WOLVENKIT_DIR (the folder holding WolvenKit.CLI.exe; only needed
# until <WorkRoot>\tools\wk7 exists).
param(
    [string]$GameDir = $env:W3_GAME_DIR,
    [string]$WorkRoot = $env:W3_WORK,
    [string]$WolvenKitDir = $env:W3_WOLVENKIT_DIR
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$env:PYTHONIOENCODING = 'utf-8'
if (-not $GameDir) { throw 'Set W3_GAME_DIR (or pass -GameDir): the game folder holding content\content0\bundles' }
if (-not $WorkRoot) { throw 'Set W3_WORK (or pass -WorkRoot): a work root outside any synced folder' }
$env:W3_WORK = $WorkRoot
$S = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts'
$W = $WorkRoot
$B = "$GameDir\content\content0\bundles"
New-Item -ItemType Directory -Force "$W\scratch", "$W\uncook", "$W\extract_items", "$W\build\templates", "$W\tools" | Out-Null

# WolvenKit 7 CLI copy with the .NET runtime sku lowered to 4.8 (the project machine has 4.8, not 4.8.1)
if (-not (Test-Path "$W\tools\wk7\WolvenKit.CLI.exe")) {
    if (-not $WolvenKitDir -or -not (Test-Path "$WolvenKitDir\WolvenKit.CLI.exe")) {
        throw 'Set W3_WOLVENKIT_DIR (or pass -WolvenKitDir) to the extracted WolvenKit 7 nightly folder holding WolvenKit.CLI.exe'
    }
    Copy-Item -Recurse $WolvenKitDir "$W\tools\wk7"
    foreach ($c in Get-ChildItem "$W\tools\wk7\*.exe.config") {
        (Get-Content $c.FullName -Raw).Replace('.NETFramework,Version=v4.8.1', '.NETFramework,Version=v4.8') |
            Set-Content $c.FullName -NoNewline -Encoding utf8
    }
}
# full bundle listing (used by build_mod.py to find every Geralt bodypart template)
python -B "$S\w3bundle.py" list -v $B | Out-File -Encoding utf8 "$W\scratch\all_bundles.tsv"
# vanilla resources (later bundles win, like the game)
python -B "$S\w3bundle.py" extract $B --overwrite -o "$W\uncook" `
    -p 'characters\base_entities\man_base\man_base.w2rig' `
    -p 'characters\models\geralt\body\model\*_mg__body*.w2mesh*' `
    -p 'characters\models\geralt\head\model\h_01_mg__geralt*' `
    -p 'characters\models\geralt\coif\model\c_02_mg__half_tail*' `
    -p 'animations\man\movement\man_geralt_movement.w2anims*'
python -B "$S\w3bundle.py" extract $B --overwrite -o "$W\extract_items" -p 'items\bodyparts\geralt_items\*' -p 'dlc\*\items\bodyparts\geralt_items\*'
Copy-Item "$W\extract_items\items\bodyparts\geralt_items\trunk\bare\t_01_mg__body.w2ent" "$W\scratch\" -Force
Copy-Item "$W\extract_items\items\bodyparts\geralt_items\coif\c_01_mg__witcher.w2ent" "$W\scratch\" -Force
Copy-Item "$W\extract_items\items\bodyparts\geralt_items\heads\h_01_mg__geralt.w2ent" "$W\scratch\" -Force
& "$PSScriptRoot\wk.ps1" -Mode cr2w2json -InputPath "$W\scratch\t_01_mg__body.w2ent", "$W\scratch\c_01_mg__witcher.w2ent", "$W\scratch\h_01_mg__geralt.w2ent", `
    "$W\uncook\characters\models\geralt\coif\model\c_02_mg__half_tail.w3dyng", `
    "$W\uncook\characters\models\geralt\head\model\h_01_mg__geralt.w3fac"
# empty item template (bare-torso template without its mesh component)
python -B "$S\make_empty_item_template.py" "$W\scratch\t_01_mg__body.w2ent.json" "$W\build\templates\empty_item.w2ent.json"
& "$PSScriptRoot\wk.ps1" -Mode json2cr2w -InputPath "$W\build\templates\empty_item.w2ent.json"
'prepared'
