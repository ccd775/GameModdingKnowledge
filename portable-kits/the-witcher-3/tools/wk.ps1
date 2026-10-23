# WolvenKit 7 CLI wrapper: wk.ps1 -Mode cr2w2json|json2cr2w -Input <file> [-Output <file>] [-Exe <WolvenKit.CLI.exe>]
# Default -Exe: <W3_WORK>\tools\wk7\WolvenKit.CLI.exe (the copy made by prepare.ps1).
param(
    [Parameter(Mandatory = $true)][ValidateSet('cr2w2json', 'json2cr2w', 'cr2w2info')][string]$Mode,
    [Parameter(Mandatory = $true)][string[]]$InputPath,
    [string]$Output = '',
    [int]$TimeoutSec = 180,
    [string]$Exe = ''
)
$wk = if ($Exe) { $Exe } elseif ($env:W3_WORK) { "$env:W3_WORK\tools\wk7\WolvenKit.CLI.exe" } else { throw 'Set W3_WORK or pass -Exe' }
$failed = 0
foreach ($in in $InputPath) {
    $argsList = @('--input', "`"$in`"", "--$Mode")
    if ($Output -and $InputPath.Count -eq 1) { $argsList += @('--output', "`"$Output`"") }
    $log = [System.IO.Path]::GetTempFileName()
    $p = Start-Process -FilePath $wk -ArgumentList $argsList -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err"
    if (-not $p.WaitForExit($TimeoutSec * 1000)) {
        $p | Stop-Process -Force
        Write-Output "TIMEOUT $in"
        $failed++
        continue
    }
    $text = Get-Content $log -Raw
    if ($p.ExitCode -ne 0 -or $text -match 'ERROR') {
        Write-Output "FAIL($($p.ExitCode)) $in"
        Write-Output $text
        $failed++
    }
    else {
        Write-Output "OK $in"
    }
    Remove-Item $log, "$log.err" -ErrorAction SilentlyContinue
}
if ($failed) { throw "WolvenKit conversion failed for $failed file(s)" }
