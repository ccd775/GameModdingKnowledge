[CmdletBinding()]
param(
    [string]$AtkDir = $env:ACO_ATK_DIR,
    [string]$DotnetRoot = $env:ACO_DOTNET_ROOT,
    [string]$ListsDir = $env:ACO_ATK_LISTS,
    [string]$OutDir,
    [string]$RuntimeVersion = '9.0.18'
)
# Builds AcoHarness.dll with the SDK's Roslyn against the portable .NET 9 runtime
# and AnvilToolkit.dll, then copies AnvilToolkit + its Libs next to it.
# Portable kit: every machine path is a parameter or an environment variable (no written-in folder):
#   -AtkDir     / ACO_ATK_DIR      unpacked AnvilToolkit 1.3.6 (AnvilToolkit.dll, AnvilToolkit.dll.config, Libs\)
#   -DotnetRoot / ACO_DOTNET_ROOT  .NET 9 runtime folder (shared\Microsoft.NETCore.App\<RuntimeVersion>, shared\Microsoft.WindowsDesktop.App\<RuntimeVersion>)
#   -ListsDir   / ACO_ATK_LISTS    folder with Odyssey.gfl (copied to <OutDir>\Lists)
#   -OutDir     / the folder of ACO_HARNESS (the AcoHarness.dll path build_mod.py runs)
# The .NET SDK (dotnet on PATH, csc.dll under Program Files) only compiles; the harness runs on the runtime above.
$ErrorActionPreference = 'Stop'
if (-not $OutDir -and $env:ACO_HARNESS) { $OutDir = Split-Path -Parent $env:ACO_HARNESS }
if (-not $AtkDir) { throw 'set ACO_ATK_DIR (unpacked AnvilToolkit 1.3.6) or pass -AtkDir' }
if (-not $DotnetRoot) { throw 'set ACO_DOTNET_ROOT (.NET 9 runtime folder) or pass -DotnetRoot' }
if (-not $ListsDir) { throw 'set ACO_ATK_LISTS (folder with Odyssey.gfl) or pass -ListsDir' }
if (-not $OutDir) { throw 'set ACO_HARNESS (<output folder>\AcoHarness.dll) or pass -OutDir' }
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$output = $OutDir
$sdk = (dotnet --list-sdks | Select-Object -Last 1).Split(' ')[0]
$compiler = Join-Path ${env:ProgramFiles} "dotnet\sdk\$sdk\Roslyn\bincore\csc.dll"
$fx = @(
    (Join-Path $DotnetRoot "shared\Microsoft.NETCore.App\$RuntimeVersion"),
    (Join-Path $DotnetRoot "shared\Microsoft.WindowsDesktop.App\$RuntimeVersion")
)
$refs = foreach ($d in $fx) {
    Get-ChildItem -LiteralPath $d -Filter '*.dll' | Where-Object {
        try { [void][System.Reflection.AssemblyName]::GetAssemblyName($_.FullName); $true } catch { $false }
    }
}
$refs = $refs | Sort-Object Name -Unique
$libs = Get-ChildItem -LiteralPath (Join-Path $AtkDir 'Libs') -Filter '*.dll' | Where-Object {
    try { [void][System.Reflection.AssemblyName]::GetAssemblyName($_.FullName); $true } catch { $false }
}
New-Item -ItemType Directory -Path $output -Force | Out-Null
$compilerArgs = @($compiler, '-noconfig', '-nostdlib+', '-langversion:latest', '-nullable:disable',
    '-target:exe', '-nowarn:CS1701,CS1702,CS8632', "-out:$output\AcoHarness.dll")
$compilerArgs += $refs | ForEach-Object { "-r:$($_.FullName)" }
$compilerArgs += $libs | ForEach-Object { "-r:$($_.FullName)" }
$compilerArgs += "-r:$(Join-Path $AtkDir 'AnvilToolkit.dll')"
$compilerArgs += Get-ChildItem -LiteralPath $projectDir -Filter '*.cs' | ForEach-Object FullName
dotnet @compilerArgs
if ($LASTEXITCODE -ne 0) { throw "csc failed: $LASTEXITCODE" }
Copy-Item (Join-Path $AtkDir 'AnvilToolkit.dll') $output -Force
Copy-Item (Join-Path $AtkDir 'AnvilToolkit.dll.config') $output -Force -ErrorAction SilentlyContinue
Get-ChildItem (Join-Path $AtkDir 'Libs') -File | Copy-Item -Destination $output -Force
New-Item -ItemType Directory -Path (Join-Path $output 'Libs') -Force | Out-Null
Get-ChildItem (Join-Path $AtkDir 'Libs') -File | Copy-Item -Destination (Join-Path $output 'Libs') -Force
New-Item -ItemType Directory -Path (Join-Path $output 'Lists') -Force | Out-Null
Get-ChildItem $ListsDir -File | Copy-Item -Destination (Join-Path $output 'Lists') -Force
@'
{
  "runtimeOptions": {
    "tfm": "net9.0",
    "frameworks": [
      { "name": "Microsoft.NETCore.App", "version": "9.0.0" },
      { "name": "Microsoft.WindowsDesktop.App", "version": "9.0.0" }
    ],
    "configProperties": {
      "System.Runtime.Serialization.EnableUnsafeBinaryFormatterSerialization": false
    }
  }
}
'@ | Set-Content -Encoding utf8 (Join-Path $output 'AcoHarness.runtimeconfig.json')
Write-Output "$output\AcoHarness.dll"
