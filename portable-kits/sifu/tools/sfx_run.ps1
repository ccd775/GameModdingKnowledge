# Usage: sfx_run.ps1 <outSub> <cmd> <args...>   (runs SifuExport against the installed Sifu paks)
# The game's pak key comes from SIFU_AES (or -Aes); it is never stored in this script. Paks: <SIFU_GAME_DIR>\Sifu\Content\Paks.
# Output: <SIFU_WORK_ROOT>\cache\<outSub>. SifuExport.exe: -Exe, default <SIFU_WORK_ROOT>\tools\SifuExport\SifuExport.exe.
[CmdletBinding(PositionalBinding = $false)]
param([Parameter(Mandatory, Position = 0)][string]$OutSub, [Parameter(Mandatory, Position = 1)][string]$Cmd,
      [string]$Aes = $env:SIFU_AES, [string]$GameDir = $env:SIFU_GAME_DIR, [string]$WorkRoot = $env:SIFU_WORK_ROOT,
      [string]$Exe, [Parameter(ValueFromRemainingArguments)][string[]]$Rest)
if (-not $Aes) { throw 'Set SIFU_AES (or pass -Aes) to the game pak key (0x...)' }
if (-not $GameDir) { throw 'Set SIFU_GAME_DIR (or pass -GameDir) to the Sifu install folder' }
if (-not $WorkRoot) { throw 'Set SIFU_WORK_ROOT (or pass -WorkRoot) to the working folder' }
if (-not $Exe) { $Exe = Join-Path $WorkRoot 'tools\SifuExport\SifuExport.exe' }
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:SIFU_AES = $Aes
$env:SIFU_GAME = 'GAME_UE4_26'
& $Exe (Join-Path $GameDir 'Sifu\Content\Paks') (Join-Path (Join-Path $WorkRoot 'cache') $OutSub) $Cmd @Rest
