# run_all.ps1 [-Run <build dir>] [-Mod original|pt]: every UE step for both variants (import, young import, materials,
# brightness, cloth adult / young, blink anim blueprints, morph check), the versioned cook and the container in <Root>\out.
# Port of the project's run_all.cmd. Progress in logs\run_all.txt ("ok <step>", "FAIL <step>", "DONE"); stops at the
# first failed step. -Mod pt runs the Karin_PicodraTech forks from scripts\ue\pt (the other steps from scripts\ue) and
# writes z_KarinPT_P; give it its own -Root (the project kept a second copy of the UE project for it).
param([string]$Run, [ValidateSet('original', 'pt')][string]$Mod = 'original',
      [string]$Root = $env:PBZ_ROOT, [string]$UE = $env:UE_ROOT,
      [string]$Scripts = (Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\ue'))
$ErrorActionPreference = 'Stop'
if (-not $Run -or -not $Root -or -not $UE) { throw 'need -Run <build dir> and -Root / PBZ_ROOT, -UE / UE_ROOT' }
$env:PBZ_ROOT = $Root; $env:UE_ROOT = $UE
$logs = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$progress = Join-Path $logs 'run_all.txt'
"start $(Get-Date -Format s) mod $Mod run $Run" | Set-Content $progress
function Add-Shared([string]$Path, [string]$Text) {
    # a helper the editor leaves running can still hold the redirected log open without write sharing: then the line goes
    # to <log>.exit.txt instead
    try { $fs = [IO.File]::Open($Path, [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite) }
    catch [IO.IOException] { $fs = [IO.File]::Open("$Path.exit.txt", [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite) }
    try { $b = [Text.Encoding]::UTF8.GetBytes($Text + "`r`n"); $fs.Write($b, 0, $b.Length) } finally { $fs.Dispose() }
}
function Note([string]$t) { Add-Shared $progress "$t $(Get-Date -Format HH:mm:ss)" }
function Step([string]$file, [string]$name, [string]$marker, [string[]]$a) {
    $py = Join-Path $Scripts $file
    if ($Mod -eq 'pt' -and (Test-Path (Join-Path $Scripts "pt\$file"))) { $py = Join-Path $Scripts "pt\$file" }
    if ($a) { & (Join-Path $PSScriptRoot 'ue_run.ps1') $py $name @a } else { & (Join-Path $PSScriptRoot 'ue_run.ps1') $py $name }
    if (-not (Select-String -Path (Join-Path $logs "$name.out.txt") -SimpleMatch $marker -Quiet -ErrorAction SilentlyContinue)) { Note "FAIL $name"; exit 1 }
    Note "ok $name"
}
$r = $Run.Replace('\', '/')
Step 'ue_import_pbz.py' 'imp' 'IMPORT_OK' @($r)
Step 'ue_import_young.py' 'young' 'IMPORT_YOUNG_OK' @($r)
Step 'ue_fixmats.py' 'fixmats' 'FIXMATS_OK' @($r)
Step 'ue_brightness.py' 'bright' 'BRIGHTNESS_OK' @()
Step 'ue_cloth.py' 'clotha' 'CLOTH_OK adult' @($r, 'adult')
Step 'ue_cloth.py' 'clothy' 'CLOTH_OK young' @($r, 'young')
Step 'ue_blink.py' 'blink' 'BLINK_OK' @()
Step 'ue_morphdump.py' 'morph1' 'MORPHDUMP_OK' @()
& (Join-Path $PSScriptRoot 'cook.ps1')
# the COOKEXIT line can lose the race with the editor still holding cook.txt: judge by the cook summary
if (-not (Select-String -Path (Join-Path $logs 'cook.txt') -SimpleMatch 'Success - 0 error(s)' -Quiet -ErrorAction SilentlyContinue)) { Note 'FAIL cook'; exit 1 }
Note 'ok cook'
$name = @{ original = 'z_KarinPBZ_P'; pt = 'z_KarinPT_P' }[$Mod]
Remove-Item (Join-Path $Root "out\$name.pak") -ErrorAction SilentlyContinue
try { & (Join-Path $PSScriptRoot 'mkcontainer.ps1') -Mod $Mod -Root $Root -UE $UE *>&1 | ForEach-Object { Add-Shared $progress "$_" } }
catch { Add-Shared $progress "$_"; Note 'FAIL container'; exit 1 }
Note 'DONE'
