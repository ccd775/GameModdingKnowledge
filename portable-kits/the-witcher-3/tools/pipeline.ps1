# Karin -> Geralt build pipeline (run tools/prepare.ps1 once first).
#   pipeline.ps1 [-BuildArgs '{"tail_scale":0.75}'] [-SkipBlender] [-Deploy] [-ModName modKarinReplacer] [-Wind 0] [-Gravity 0] [-Dampening 0.95]
#                [-WorkRoot <dir>] [-Blender <blender.exe>] [-GameDir <game>]
# Defaults: -WorkRoot $env:W3_WORK, -Blender $env:W3_BLENDER, -GameDir $env:W3_GAME_DIR (only -Deploy and Blender need it).
# karin_build.py also needs $env:W3_SOURCE_FBX (see scripts/w3paths.py).
param(
    [string]$BuildArgs = '{"stage":"all"}',
    [switch]$SkipBlender,
    [switch]$Deploy,
    [string]$ModName = 'modKarinReplacer',
    [ValidateSet('stub', 'drop')][string]$Fur = 'drop',
    [double]$Wind = 0.0,     # no wind in Karin's VRM; with gravity off any wind holds the chains to one side
    [double]$Gravity = 0.0,  # dyng constraint gravity; Karin's VRM springs have none (chains keep their shape)
    [double]$Dampening = -1, # dyng constraint dampening; < 0 leaves it unset like vanilla (0.985 tested worse)
    [string]$WorkRoot = $env:W3_WORK,
    [string]$Blender = $env:W3_BLENDER,
    [string]$GameDir = $env:W3_GAME_DIR
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true   # any non-zero exit (python, wk.ps1) aborts the pipeline
$env:PYTHONIOENCODING = 'utf-8'
if (-not $WorkRoot) { throw 'Set W3_WORK (or pass -WorkRoot): the work root filled by tools/prepare.ps1' }
if (-not $SkipBlender -and -not $Blender) { throw 'Set W3_BLENDER (or pass -Blender): Blender 5.0 blender.exe with the Witcher3-Blender-Tools add-on' }
if ($Deploy -and -not $GameDir) { throw 'Set W3_GAME_DIR (or pass -GameDir) for -Deploy' }
$env:W3_WORK = $WorkRoot
if ($GameDir) { $env:W3_GAME_DIR = $GameDir }
$S = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts'
$W = $WorkRoot
$T = "$W\build\templates"

if (-not $SkipBlender) {
    & $Blender --background --factory-startup --python "$S\blender\karin_build.py" -- $BuildArgs *> "$W\scratch\build.log"
    $log = Get-Content "$W\scratch\build.log" -Raw
    if ($log -notmatch '\[karin_build\] DONE') {
        Select-String -Path "$W\scratch\build.log" -Pattern 'Traceback|Error' -Context 0, 12 | Select-Object -First 3
        throw 'karin_build failed'
    }
    $stubArgs = @{ out = "$W\build\depot\characters\models\geralt\head\model\h_mg__neck_transition.w2mesh"; bone = 'neck' } | ConvertTo-Json -Compress
    & $Blender --background --factory-startup --python "$S\blender\make_stub_mesh.py" -- $stubArgs *> "$W\scratch\stub.log"
}
$rep = Get-Content "$W\scratch\karin_build_report.json" -Raw | ConvertFrom-Json
if ($rep.cfg.physics) {
    # dyng resource + item template with a dangle component (mesh skinned to the dangle skeleton)
    $dyngJson = "$W\build\karin_body.w3dyng.json"
    python -B "$S\make_dyng.py" "$W\build\karin_dyng_spec.json" "$W\uncook\characters\models\geralt\coif\model\c_02_mg__half_tail.w3dyng.json" $dyngJson
    & "$PSScriptRoot\wk.ps1" -Mode json2cr2w -InputPath $dyngJson | Out-Null
    # WolvenKit writes SSkeletonBone.name as StringAnsi; the dangle skeleton only works with the vanilla String form
    python -B "$S\fix_cr2w_skeleton_names.py" "$W\build\karin_body.w3dyng" "$W\build\depot\characters\models\karin\karin_body.w3dyng"
    Copy-Item "$W\build\depot\characters\models\geralt\head\model\h_mg__neck_transition.w2mesh" "$W\build\depot\characters\models\karin\karin_stub.w2mesh" -Force
    # dangle components work in hairstyle (coif) items; Karin rides in every coif template, heads stay empty
    python -B "$S\make_dangle_item_template.py" "$W\scratch\c_01_mg__witcher.w2ent.json" "$T\karin_coif_item.w2ent.json" 'characters\models\karin\karin_body.w3dyng' 'characters\models\karin\karin_body.w2mesh' 'characters\models\karin\karin_stub.w2mesh' --fur $Fur --wind $Wind --gravity $Gravity @(if ($Dampening -ge 0) { '--dampening', $Dampening })
    & "$PSScriptRoot\wk.ps1" -Mode json2cr2w -InputPath "$T\karin_coif_item.w2ent.json" | Out-Null
    $stageArgs = @('--empty', "$T\empty_item.w2ent", '--coif', "$T\karin_coif_item.w2ent")
    if ($rep.cfg.face) {
        # face: Karin's own CMimicFace (bones fitted to her shape keys) + head item with a CMimicComponent
        $facJson = "$W\build\karin_face.w3fac.json"
        python -B "$S\make_w3fac.py" "$W\build\karin_face_spec.json" "$W\uncook\characters\models\geralt\head\model\h_01_mg__geralt.w3fac.json" $facJson
        & "$PSScriptRoot\wk.ps1" -Mode json2cr2w -InputPath $facJson | Out-Null
        python -B "$S\fix_cr2w_skeleton_names.py" "$W\build\karin_face.w3fac" "$W\build\depot\characters\models\karin\karin_face.w3fac"
        python -B "$S\make_head_item_template.py" "$W\scratch\h_01_mg__geralt.w2ent.json" "$T\karin_head_face_item.w2ent.json" 'characters\models\karin\karin_face.w3fac' 'characters\models\karin\karin_face.w2mesh' 'characters\models\karin\karin_stub.w2mesh'
        & "$PSScriptRoot\wk.ps1" -Mode json2cr2w -InputPath "$T\karin_head_face_item.w2ent.json" | Out-Null
        $stageArgs += @('--head', "$T\karin_head_face_item.w2ent")
    }
    else {
        Remove-Item "$W\build\depot\characters\models\karin\karin_face.*" -ErrorAction SilentlyContinue
    }
}
else {
    Remove-Item "$W\build\depot\characters\models\karin\karin_body.w3dyng" -ErrorAction SilentlyContinue
    python -B "$S\make_mesh_item_template.py" "$W\scratch\t_01_mg__body.w2ent.json" "$T\karin_head_item.w2ent.json" 'characters\models\karin\karin_body.w2mesh' karin_body -0.75 -0.8 -0.02 0.75 0.4 2.2
    & "$PSScriptRoot\wk.ps1" -Mode json2cr2w -InputPath "$T\karin_head_item.w2ent.json" | Out-Null
    $stageArgs = @('--empty', "$T\empty_item.w2ent", '--head', "$T\karin_head_item.w2ent")
}
python -B "$S\build_mod.py" stage "$W\build\stage_m1" @stageArgs --extra "$W\build\depot"
python -B "$S\build_mod.py" pack "$W\build\stage_m1" "$W\build\mods\$ModName"
python -B "$S\w3metadata_write.py" "$W\build\mods\$ModName\content"
Get-ChildItem "$W\build\mods\$ModName\content" | ForEach-Object { '{0}  {1}  {2}' -f $_.Name, $_.Length, (Get-FileHash $_.FullName).Hash }

if ($Deploy) {
    Get-Process witcher3 -ErrorAction SilentlyContinue | Stop-Process -Force
    $t = 0
    while ((Get-Process witcher3 -ErrorAction SilentlyContinue) -and $t -lt 60) { Start-Sleep -Milliseconds 500; $t++ }
    Start-Sleep -Seconds 2   # the bundle handle is released a moment after the process disappears
    $dst = "$GameDir\mods\$ModName\content"
    New-Item -ItemType Directory -Force $dst | Out-Null
    Copy-Item "$W\build\mods\$ModName\content\*" $dst -Force
    Start-Process -FilePath "$GameDir\bin\x64_dx12\witcher3.exe" -WorkingDirectory "$GameDir\bin\x64_dx12"
    'deployed + launched'
}
