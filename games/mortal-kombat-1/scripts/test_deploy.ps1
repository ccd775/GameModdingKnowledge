$ErrorActionPreference = 'Stop'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('mk1-playbook-test-' + [Guid]::NewGuid().ToString('N'))
$source = Join-Path $testRoot 'source'
$paks = Join-Path $testRoot 'game/MK12/Content/Paks'
$backups = Join-Path $testRoot 'backups'
New-Item -ItemType Directory -Path $source,$paks | Out-Null
# Process control is mocked ONLY in this synthetic filesystem test.
function Get-Process { [CmdletBinding()]param([string]$Name) return @() }
$hashes = @{}
foreach ($ext in @('pak','ucas','utoc')) {
    Set-Content -LiteralPath (Join-Path $source "a_new_P.$ext") -Value "new-$ext" -Encoding ASCII
    Set-Content -LiteralPath (Join-Path $paks "a_test_P.$ext") -Value "old-$ext" -Encoding ASCII
    $hashes[$ext] = (Get-FileHash -LiteralPath (Join-Path $source "a_new_P.$ext")).Hash
}
$hashPath = Join-Path $testRoot 'hashes.json'
$hashes | ConvertTo-Json | Set-Content -LiteralPath $hashPath -Encoding UTF8
$arguments = @{SourceDirectory=$source; SourcePrefix='a_new_P'; GamePaksPath=$paks; InstalledPrefix='a_test_P'; ExpectedHashesJson=$hashPath; BackupRoot=$backups}
$scriptPath = Join-Path $PSScriptRoot 'deploy_trio.ps1'
& $scriptPath @arguments | Out-Null
if (Test-Path -LiteralPath $backups) { throw 'Preflight wrote backup' }
& $scriptPath @arguments -Install | Out-Null
foreach ($ext in $hashes.Keys) {
    if ((Get-FileHash -LiteralPath (Join-Path $paks "a_test_P.$ext")).Hash -ne $hashes[$ext]) { throw 'Install test failed' }
}
$rejected=0
$bad=$arguments.Clone();$bad['BackupRoot']=$paks
try { & $scriptPath @bad | Out-Null } catch { $rejected++ }
$bad=$arguments.Clone();$bad['InstalledPrefix']='pakchunk7-WindowsNoEditor'
try { & $scriptPath @bad | Out-Null } catch { $rejected++ }
$bad=$arguments.Clone();$bad['InstalledPrefix']='../escape'
try { & $scriptPath @bad | Out-Null } catch { $rejected++ }
$hashes['pak']='0'*64
$hashes | ConvertTo-Json | Set-Content -LiteralPath $hashPath -Encoding UTF8
try { & $scriptPath @arguments | Out-Null } catch { $rejected++ }
if ($rejected -ne 4) { throw 'Expected safety rejections missing' }
[pscustomobject]@{Passed=$true; SafetyRejections=$rejected; Scope='Synthetic preflight/install and hash/path guards; no game touched'; FixtureDirectory=$testRoot} | ConvertTo-Json
