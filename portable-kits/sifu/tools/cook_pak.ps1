# Cook the Sifu mod project and build the mod pak from an include list.
# Usage: cook_pak.ps1 <PakName> [-AssetDir <folder under Characters\MainChar\W, default Karin>] [-NoCook]
# UE 4.26 install: SIFU_UE_ROOT (or -UERoot). Working folder: SIFU_WORK_ROOT (or -WorkRoot; logs\, out\).
# Project folder: SIFU_PROJECT (or -Project), default <WorkRoot>\SifuProj. Game: SIFU_GAME_DIR (or -GameDir); the
# game's own pakchunk0-WindowsNoEditor.sig is copied as the mod's .sig.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Mandatory, Position = 0)][string]$PakName, [Parameter(Position = 1)][string]$AssetDir = 'Karin', [switch]$NoCook,
      [string]$WorkRoot = $env:SIFU_WORK_ROOT, [string]$UERoot = $env:SIFU_UE_ROOT, [string]$Project = $env:SIFU_PROJECT,
      [string]$GameDir = $env:SIFU_GAME_DIR)
$ErrorActionPreference = 'Stop'
if (-not $WorkRoot) { throw 'Set SIFU_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $UERoot) { throw 'Set SIFU_UE_ROOT (or pass -UERoot) to the UE 4.26 install folder' }
if (-not $GameDir) { throw 'Set SIFU_GAME_DIR (or pass -GameDir) to the Sifu install folder' }
if (-not $Project) { $Project = Join-Path $WorkRoot 'SifuProj' }
$UE = Join-Path $UERoot 'Engine\Binaries\Win64'
$Proj = (Resolve-Path -LiteralPath $Project).ProviderPath.TrimEnd('\')
$Logs = Join-Path $WorkRoot 'logs'
$Out = Join-Path $WorkRoot 'out'
$Cooked = "$Proj\Saved\Cooked\WindowsNoEditor\Sifu\Content"
New-Item -ItemType Directory -Force $Logs, $Out | Out-Null
if (-not $NoCook) {
  & "$UE\UE4Editor-Cmd.exe" "$Proj\Sifu.uproject" -run=cook -targetplatform=WindowsNoEditor "-cookdir=$Proj\Content" -unattended -nop4 -nosplash -NoLogTimes > "$Logs\cook.log" 2>&1
  "cook exit=$LASTEXITCODE"
  Select-String -Path "$Logs\cook.log" -Pattern 'Error:|Warning: .*(SK_W|Karin)|LogCook: Display: Done|Success - ' | Select-Object -Last 15 | ForEach-Object { $_.Line }
}
# include only our own assets (game-owned placeholders are excluded)
$include = @('Characters\MainChar\W\Meshes\SK_W_MainChar_01.', "Characters\MainChar\W\$AssetDir\")
$files = Get-ChildItem $Cooked -Recurse -File | Where-Object { $rel = $_.FullName.Substring($Cooked.Length + 1); ($include | Where-Object { $rel.StartsWith($_) }).Count -gt 0 }
$resp = "$Out\$PakName.txt"
$lines = foreach ($f in $files) { $rel = $f.FullName.Substring($Cooked.Length + 1).Replace('\', '/'); "`"$($f.FullName)`" `"../../../Sifu/Content/$rel`"" }
$lines | Set-Content -Encoding ASCII $resp
"files=$($files.Count)"
$pak = "$Out\$PakName.pak"
& "$UE\UnrealPak.exe" $pak "-create=$resp" -compress > "$Logs\unrealpak.log" 2>&1
"unrealpak exit=$LASTEXITCODE"
Copy-Item (Join-Path $GameDir 'Sifu\Content\Paks\pakchunk0-WindowsNoEditor.sig') "$Out\$PakName.sig" -Force
Get-Item $pak, "$Out\$PakName.sig" | ForEach-Object { "{0} {1:N0}" -f $_.Name, $_.Length }
