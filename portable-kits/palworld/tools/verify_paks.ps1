# Parse our own paks with CUE4Parse (game usmap) and dump what the game will read.
# Usage: pwsh -File verify_paks.ps1 -Tag r3
# Working folder: PAL_WORK_ROOT (or -WorkRoot): paks from out\<tag>\, dumps to extract\verify_<tag>\.
# PalExport.exe: -Exe, default <WorkRoot>\tools\PalExport\PalExport.exe. usmap: PAL_USMAP (or -Usmap), default
# <WorkRoot>\tools\Mappings.usmap. Oodle DLL: PAL_OODLE (or -Oodle), default <WorkRoot>\tools\oo2core_9_win64.dll.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Position = 0)][string]$Tag = 'dev', [string]$WorkRoot = $env:PAL_WORK_ROOT, [string]$Exe,
      [string]$Usmap = $env:PAL_USMAP, [string]$Oodle = $env:PAL_OODLE)
if (-not $WorkRoot) { throw 'Set PAL_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $Exe) { $Exe = Join-Path $WorkRoot 'tools\PalExport\PalExport.exe' }
if (-not $Usmap) { $Usmap = Join-Path $WorkRoot 'tools\Mappings.usmap' }
if (-not $Oodle) { $Oodle = Join-Path $WorkRoot 'tools\oo2core_9_win64.dll' }
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$paks = Join-Path $WorkRoot "out\$Tag"
$out = Join-Path $WorkRoot "extract\verify_$Tag"
Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
& $exe $paks $usmap $oodle $out list '.' 2>&1 | Select-Object -First 400
$P = '/Game/Pal/Model/Character/Player'
& $exe $paks $usmap $oodle $out skel "$P/Outfit/SK_Player_Female_Outfit_OldCloth001/SK_Player_Female_Outfit_OldCloth001" "$P/Head/Head001/SK_Player_Female_Head001" "$P/Head/Head026/SK_Player_Female_Head026" "$P/Hair/Hair001/SK_Player_Hair001" 2>&1
& $exe $paks $usmap $oodle $out json "/Game/Pal/Blueprint/Character/Player/Imp_Cloth/ABP_F_OldCloth001_Implimentation" "$P/Outfit/SK_Player_Female_Outfit_OldCloth001/SK_Player_Female_Outfit_OldCloth001" "/Game/Mods/KarinPal/Materials/MI_Karin_Skin" "/Game/Mods/KarinPal/Materials/MI_Karin_Hair" "/Game/Mods/KarinPal/Materials/MI_Karin_Costume" "/Game/Mods/KarinPal/Materials/MI_Karin_Face" "$P/Head/Head001/SK_Player_Female_Head001" 2>&1
"VERIFY_DONE"
