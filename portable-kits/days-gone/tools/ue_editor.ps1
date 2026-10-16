# Open the UE 4.11 BendGame mod project in the editor (port of the build machine's ue411.bat). Close the editor before
# cook.ps1 and before starting the game: the game exits after about 2 s while the editor has this project open.
# UE 4.11: DG_UE_ROOT (or -UERoot). Project folder with BendGame.uproject: DG_PROJECT (or -Project), default
# <DG_WORK_ROOT>\U411\BendGame (DG_WORK_ROOT or -WorkRoot).
[CmdletBinding(PositionalBinding = $false)]
param([string]$UERoot = $env:DG_UE_ROOT, [string]$Project = $env:DG_PROJECT, [string]$WorkRoot = $env:DG_WORK_ROOT)
if (-not $UERoot) { throw 'Set DG_UE_ROOT (or pass -UERoot) to the UE 4.11 install folder' }
if (-not $Project) {
  if (-not $WorkRoot) { throw 'Set DG_PROJECT (or pass -Project) to the BendGame project folder, or DG_WORK_ROOT for <DG_WORK_ROOT>\U411\BendGame' }
  $Project = Join-Path $WorkRoot 'U411\BendGame'
}
Start-Process (Join-Path $UERoot 'Engine\Binaries\Win64\UE4Editor.exe') -ArgumentList ('"' + (Join-Path $Project 'BendGame.uproject') + '"')
