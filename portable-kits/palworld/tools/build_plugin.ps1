# Build the project plugins (KawaiiPhysics, PalModTools) for the UE 5.1 editor.
# UE 5.1 install: PAL_UE_ROOT (or -UERoot). Project folder with Pal.uproject (plugins in its Plugins\): PAL_PROJECT
# (or -Project), default <PAL_WORK_ROOT>\UEProject\Pal (PAL_WORK_ROOT or -WorkRoot). -Compiler: UBT compiler switch,
# default VisualStudio2019 (what the project used).
[CmdletBinding(PositionalBinding = $false)]
param([string]$UERoot = $env:PAL_UE_ROOT, [string]$Project = $env:PAL_PROJECT, [string]$WorkRoot = $env:PAL_WORK_ROOT,
      [string]$Compiler = 'VisualStudio2019')
if (-not $UERoot) { throw 'Set PAL_UE_ROOT (or pass -UERoot) to the UE 5.1 install folder' }
if (-not $Project) {
    if (-not $WorkRoot) { throw 'Set PAL_PROJECT (or pass -Project) to the folder with Pal.uproject, or PAL_WORK_ROOT (or -WorkRoot)' }
    $Project = Join-Path $WorkRoot 'UEProject\Pal'
}
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$ubt = Join-Path $UERoot 'Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe'
& $ubt Development Win64 "-Project=$(Join-Path $Project 'Pal.uproject')" -TargetType=Editor -Progress -NoHotReloadFromIDE "-Compiler=$Compiler" 2>&1 | Select-Object -Last 60
"EXIT $LASTEXITCODE"
Get-ChildItem (Join-Path $Project 'Plugins\*\Binaries\Win64') -File -ErrorAction SilentlyContinue | ForEach-Object { '{0} {1} {2}' -f $_.LastWriteTime, $_.Length, $_.FullName }
