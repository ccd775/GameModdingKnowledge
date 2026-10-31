# ue_run.ps1 <script.py> <log name> [script args...]: run a UE 5.7 editor Python script headless against the mod project.
# Port of the project's ue_run.cmd. -Root / PBZ_ROOT: work root (UE\ProjectPBZ, logs\); -UE / UE_ROOT: engine folder that
# holds Engine\. Writes logs\<log>.out.txt (stdout, last line "EXIT <code>", or in <log>.out.txt.exit.txt while a
# helper process still holds the log) and logs\<log>.ue.log. The script path is
# passed with forward slashes: the commandlet's -script= parser eats \u / \U sequences.
param([Parameter(Mandatory = $true, Position = 0)][string]$Script,
      [Parameter(Mandatory = $true, Position = 1)][string]$Log,
      [Parameter(Position = 2, ValueFromRemainingArguments = $true)][string[]]$ScriptArgs,
      [string]$Root = $env:PBZ_ROOT, [string]$UE = $env:UE_ROOT)
$ErrorActionPreference = 'Stop'
if (-not $Root -or -not $UE) { throw 'set -Root / PBZ_ROOT (work root with UE\ProjectPBZ) and -UE / UE_ROOT (UE 5.7 install)' }
$exe = Join-Path $UE 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$proj = Join-Path $Root 'UE\ProjectPBZ\ProjectPBZ.uproject'
$logs = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$line = (@($Script.Replace('\', '/')) + @($ScriptArgs | Where-Object { $_ } | ForEach-Object { $_.Replace('\', '/') })) -join ' '
function Add-Shared([string]$Path, [string]$Text) {
    # a helper the editor leaves running can still hold the redirected log open without write sharing: then the line goes
    # to <log>.exit.txt instead
    try { $fs = [IO.File]::Open($Path, [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite) }
    catch [IO.IOException] { $fs = [IO.File]::Open("$Path.exit.txt", [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite) }
    try { $b = [Text.Encoding]::UTF8.GetBytes($Text + "`r`n"); $fs.Write($b, 0, $b.Length) } finally { $fs.Dispose() }
}
function Invoke-Logged([string]$Program, [string]$ArgLine, [string]$LogFile) {
    # cmd.exe runs the raw argument string and redirects stdout + stderr, as the project's .cmd did. WaitForExit waits for
    # this process only; Start-Process -Wait would also wait for helpers the editor leaves running.
    $psi = New-Object Diagnostics.ProcessStartInfo 'cmd.exe'
    $psi.Arguments = '/d /s /c ""{0}" {1} > "{2}" 2>&1"' -f $Program, $ArgLine, $LogFile
    $psi.UseShellExecute = $false
    $proc = [Diagnostics.Process]::Start($psi)
    $proc.WaitForExit()
    return $proc.ExitCode
}
$out = Join-Path $logs "$Log.out.txt"
$code = Invoke-Logged $exe ('"{0}" -run=pythonscript -script="{1}" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput -abslog="{2}"' -f
    $proj, $line, (Join-Path $logs "$Log.ue.log")) $out
Add-Shared $out "EXIT $code"
exit $code
