[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$SourceDirectory,
    [Parameter(Mandatory=$true)][string]$SourcePrefix,
    [Parameter(Mandatory=$true)][string]$GamePaksPath,
    [Parameter(Mandatory=$true)][string]$InstalledPrefix,
    [Parameter(Mandatory=$true)][string]$ExpectedHashesJson,
    [Parameter(Mandatory=$true)][string]$BackupRoot,
    [switch]$Install
)
$ErrorActionPreference = 'Stop'
$src = (Resolve-Path -LiteralPath $SourceDirectory).Path
$paks = (Resolve-Path -LiteralPath $GamePaksPath).Path
if ((Split-Path $paks -Leaf) -ne 'Paks' -or (Split-Path (Split-Path $paks -Parent) -Leaf) -ne 'Content' -or (Split-Path (Split-Path (Split-Path $paks -Parent) -Parent) -Leaf) -ne 'MK12') { throw 'Expected MK12/Content/Paks directory' }
foreach ($prefix in @($SourcePrefix,$InstalledPrefix)) {
    if ($prefix -cnotmatch '^[az]_[A-Za-z0-9_-]+$') { throw 'Only explicitly named custom a_/z_ prefixes are allowed' }
}
$backupBase = [IO.Path]::GetFullPath($BackupRoot).TrimEnd('\')
if ($backupBase.Equals($paks,[StringComparison]::OrdinalIgnoreCase) -or $backupBase.StartsWith($paks+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Backup must be outside game Paks' }
$hashes = Get-Content -LiteralPath $ExpectedHashesJson -Raw | ConvertFrom-Json
$items = @()
foreach ($ext in @('pak','ucas','utoc')) {
    $from = Join-Path $src "$SourcePrefix.$ext"
    $to = Join-Path $paks "$InstalledPrefix.$ext"
    if ([IO.Path]::GetFullPath($from).Equals([IO.Path]::GetFullPath($to),[StringComparison]::OrdinalIgnoreCase)) { throw 'Source equals destination' }
    if (!(Test-Path -LiteralPath $from -PathType Leaf) -or (Get-Item -LiteralPath $from).Length -le 0) { throw "Missing/empty source $ext" }
    $expected = [string]$hashes.$ext
    if ($expected -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $from).Hash -ne $expected) { throw "Source hash mismatch: $ext" }
    $old = if (Test-Path -LiteralPath $to -PathType Leaf) { (Get-FileHash -LiteralPath $to).Hash } else { $null }
    $items += [pscustomobject]@{Extension=$ext; Source=$from; Target=$to; NewHash=$expected; OldHash=$old}
}
$existing = @($items | Where-Object { $_.OldHash }).Count
if ($existing -ne 0 -and $existing -ne 3) { throw 'Destination is an incomplete trio; inspect manually' }
if (Get-Process MK12 -ErrorAction SilentlyContinue) { throw 'Exit MK12 before deployment/preflight' }
if (!$Install) {
    [pscustomobject]@{Mode='preflight-only'; Items=$items; BackupRoot=$backupBase} | ConvertTo-Json -Depth 5
    return
}
$backup = Join-Path $backupBase ('trio-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($item in $items) {
    if ($item.OldHash) {
        $saved = Join-Path $backup "$InstalledPrefix.$($item.Extension)"
        Copy-Item -LiteralPath $item.Target -Destination $saved
        if ((Get-FileHash -LiteralPath $saved).Hash -ne $item.OldHash) { throw 'Backup hash mismatch; install not started' }
    }
}
$items | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $backup 'deployment.json') -Encoding UTF8
try {
    if (Get-Process MK12 -ErrorAction SilentlyContinue) { throw 'Game started during preflight' }
    foreach ($item in $items) {
        Copy-Item -LiteralPath $item.Source -Destination $item.Target
        if ((Get-FileHash -LiteralPath $item.Target).Hash -ne $item.NewHash) { throw 'Installed hash mismatch' }
    }
} catch {
    $failure = $_
    foreach ($item in $items) {
        if ($item.OldHash) {
            Copy-Item -LiteralPath (Join-Path $backup "$InstalledPrefix.$($item.Extension)") -Destination $item.Target
            if ((Get-FileHash -LiteralPath $item.Target).Hash -ne $item.OldHash) { throw "Rollback failed; inspect backup $backup" }
        } elseif (Test-Path -LiteralPath $item.Target -PathType Leaf) {
            Remove-Item -LiteralPath $item.Target
        }
    }
    throw $failure
}
[pscustomobject]@{Mode='installed'; Backup=$backup; Items=$items} | ConvertTo-Json -Depth 5
