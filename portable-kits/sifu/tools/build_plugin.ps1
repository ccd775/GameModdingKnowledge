# Build the SifuModTools editor plugin with UAT and install it into the project's Plugins folder.
# UE 4.26 install: SIFU_UE_ROOT (or -UERoot). Working folder: SIFU_WORK_ROOT (or -WorkRoot; log in logs\build_plugin.log).
# Plugin source: -Plugin, default <WorkRoot>\pluginsrc\SifuModTools\SifuModTools.uplugin (a copy of ue/SifuModTools).
# Package: -Package, default <WorkRoot>\build\SifuModTools. Project folder: SIFU_PROJECT (or -Project), default <WorkRoot>\SifuProj.
param([string]$WorkRoot = $env:SIFU_WORK_ROOT, [string]$UERoot = $env:SIFU_UE_ROOT, [string]$Project = $env:SIFU_PROJECT,
      [string]$Plugin, [string]$Package)
if (-not $WorkRoot) { throw 'Set SIFU_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $UERoot) { throw 'Set SIFU_UE_ROOT (or pass -UERoot) to the UE 4.26 install folder' }
if (-not $Project) { $Project = Join-Path $WorkRoot 'SifuProj' }
if (-not $Plugin) { $Plugin = Join-Path $WorkRoot 'pluginsrc\SifuModTools\SifuModTools.uplugin' }
if (-not $Package) { $Package = Join-Path $WorkRoot 'build\SifuModTools' }
New-Item -ItemType Directory -Force (Join-Path $WorkRoot 'logs') | Out-Null
$log = Join-Path $WorkRoot 'logs\build_plugin.log'
& (Join-Path $UERoot 'Engine\Build\BatchFiles\RunUAT.bat') BuildPlugin "-Plugin=$Plugin" "-Package=$Package" -TargetPlatforms=Win64 -Rocket > $log 2>&1
$ok = Select-String -Path $log -Pattern 'BUILD SUCCESSFUL' -Quiet
$dest = Join-Path $Project 'Plugins\SifuModTools'
if ($ok) { Remove-Item -Recurse -Force $dest -ErrorAction SilentlyContinue; Copy-Item -Recurse $Package $dest; "PLUGIN_OK" }
else { Select-String -Path $log -Pattern 'error' | Select-Object -First 15 | ForEach-Object { $_.Line } }
