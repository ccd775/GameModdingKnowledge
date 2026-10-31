# build_plugin.ps1: build the editor target of the mod project (compiles Plugins\PBZModTools). Port of the project's
# build_plugin.cmd. Needs the Visual Studio C++ build tools (the project used VS 2022 BuildTools, MSVC 14.44).
# -Root / PBZ_ROOT, -UE / UE_ROOT as ue_run.ps1. Log in logs\ubt.txt.
param([string]$Root = $env:PBZ_ROOT, [string]$UE = $env:UE_ROOT)
$ErrorActionPreference = 'Stop'
if (-not $Root -or -not $UE) { throw 'set -Root / PBZ_ROOT and -UE / UE_ROOT' }
$logs = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$log = Join-Path $logs 'ubt.txt'
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
$code = Invoke-Logged (Join-Path $UE 'Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe') ('Development Win64 -Project="{0}" -TargetType=Editor -Progress -NoHotReloadFromIDE' -f
    (Join-Path $Root 'UE\ProjectPBZ\ProjectPBZ.uproject')) $log
Add-Shared $log "UBTEXIT $code"
exit $code
