# portable kit: NxExtract driver (pwsh 7.4 / .NET 8). The project copy had this machine's paths written in.
#   -Work  folder with nx\LibHac.dll, nx\NxExtract.dll (tools/NxExtract) and title_merged.keys (yuzu title.keys)
#   -Keys  folder with prod.keys
#   -Base  '<game .xci>|<program NCA file name>' (or a base program .nca)
#   -Patch the update's program NCA (yuzu: nand\user\Contents\registered\<dir>\<id>.nca)
#   -mode ls (list) | x (extract);  -pats 'glob;glob' (no [] classes);  -out extraction folder
param([string]$mode = 'ls', [Parameter(Mandatory)][string]$out, [string]$pats = '',
      [Parameter(Mandatory)][string]$Work, [Parameter(Mandatory)][string]$Keys,
      [Parameter(Mandatory)][string]$Base, [Parameter(Mandatory)][string]$Patch)
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -Path "$Work\nx\LibHac.dll"
Add-Type -Path "$Work\nx\NxExtract.dll"
[NxExtract]::Run($mode, "$Keys\prod.keys", "$Work\title_merged.keys", $Base, $Patch, $out, $pats.Split(';'))
